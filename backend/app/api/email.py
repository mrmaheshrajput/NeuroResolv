"""
Email preferences API router.

Handles user email preferences for personalized email reflections,
and provides internal endpoints for the Lambda email scheduler.
"""

from datetime import datetime, timezone
from typing import Optional
from zoneinfo import ZoneInfo

from app.core import get_current_user
from app.db import User, UserEmailPreference, get_db, EmailQueue
from app.schemas import (
    EmailContentResponse,
    EmailPreferenceCreate,
    EmailPreferenceResponse,
    EmailType,
    ScheduledUserInfo,
    ScheduledUsersResponse,
    SendEmailRequest,
    SendEmailResponse,
    SendEmailResult,
)
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/email", tags=["Email"])


@router.get("/preferences", response_model=Optional[EmailPreferenceResponse])
async def get_email_preferences(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current user's email preferences"""
    result = await db.execute(
        select(UserEmailPreference).where(UserEmailPreference.user_id == user.id)
    )
    preference = result.scalar_one_or_none()

    if not preference:
        return None

    return EmailPreferenceResponse.model_validate(preference)


@router.put("/preferences", response_model=EmailPreferenceResponse)
async def update_email_preferences(
    data: EmailPreferenceCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create or update email preferences"""
    # Validate timezone
    try:
        ZoneInfo(data.timezone)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid timezone: {data.timezone}",
        )

    result = await db.execute(
        select(UserEmailPreference).where(UserEmailPreference.user_id == user.id)
    )
    preference = result.scalar_one_or_none()

    if preference:
        preference.email_opt_in = data.email_opt_in
        preference.timezone = data.timezone
        preference.preferred_hour = data.preferred_hour
    else:
        preference = UserEmailPreference(
            user_id=user.id,
            email_opt_in=data.email_opt_in,
            timezone=data.timezone,
            preferred_hour=data.preferred_hour,
        )
        db.add(preference)

    await db.commit()
    await db.refresh(preference)

    return EmailPreferenceResponse.model_validate(preference)


@router.delete("/preferences", status_code=status.HTTP_204_NO_CONTENT)
async def delete_email_preferences(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete email preferences (opt-out)"""
    result = await db.execute(
        select(UserEmailPreference).where(UserEmailPreference.user_id == user.id)
    )
    preference = result.scalar_one_or_none()

    if preference:
        await db.delete(preference)
        await db.commit()


@router.get("/scheduled-users", response_model=ScheduledUsersResponse)
async def get_scheduled_users(
    utc_hour: int = Query(ge=0, le=23),
    db: AsyncSession = Depends(get_db),
):
    """
    Get users scheduled to receive emails at the specified UTC hour.
    This endpoint is meant to be called by the Lambda scheduler.

    The function converts the UTC hour to each user's local timezone
    and returns those whose preferred_hour matches.
    """
    # Get all opted-in users with their preferences
    result = await db.execute(
        select(UserEmailPreference, User)
        .join(User, UserEmailPreference.user_id == User.id)
        .where(
            and_(
                UserEmailPreference.email_opt_in == True,
                User.is_active == True,
                UserEmailPreference.is_paused == False,
            )
        )
    )
    rows = result.all()

    scheduled_users = []
    utc_now = datetime.now(timezone.utc).replace(hour=utc_hour, minute=0, second=0)

    for pref, user in rows:
        try:
            # Convert UTC time to user's timezone
            user_tz = ZoneInfo(pref.timezone)
            user_local_time = utc_now.astimezone(user_tz)
            user_local_hour = user_local_time.hour

            # Check if this matches their preferred hour
            if user_local_hour == pref.preferred_hour:
                # Check if we haven't already sent an email today
                if pref.last_email_sent_at:
                    last_sent_local = pref.last_email_sent_at.replace(
                        tzinfo=timezone.utc
                    ).astimezone(user_tz)
                    if last_sent_local.date() == user_local_time.date():
                        continue  # Already sent today

                scheduled_users.append(
                    ScheduledUserInfo(
                        user_id=user.id,
                        email=user.email,
                        full_name=user.full_name,
                        timezone=pref.timezone,
                        preferred_hour=pref.preferred_hour,
                    )
                )
        except Exception as e:
            print(f"Error processing user {user.id}: {e}")
            continue

    return ScheduledUsersResponse(users=scheduled_users, utc_hour=utc_hour)


@router.post("/send", response_model=SendEmailResponse)
async def send_scheduled_emails(
    request: SendEmailRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Process and send emails for the specified user IDs.
    This endpoint is meant to be called by the Lambda scheduler.

    For each user:
    1. Determine the appropriate email type based on their data
    2. Generate personalized content using the AI agent
    3. Send the email via AWS SES
    4. Update the last_email_sent_at timestamp
    """
    from app.agents.email_reflection_agent import (
        determine_email_type,
        generate_email_content,
    )
    from app.aws.email_service import send_email

    results = []
    total_sent = 0
    total_failed = 0

    # 1. Process specifically queued emails first
    queue_result = await db.execute(
        select(EmailQueue).where(
            EmailQueue.status == "pending",
            EmailQueue.scheduled_for <= datetime.utcnow(),
        )
    )
    queued_emails = queue_result.scalars().all()
    for q_email in queued_emails:
        try:
            user_result = await db.execute(
                select(User).where(User.id == q_email.user_id)
            )
            user = user_result.scalar_one_or_none()
            if not user:
                q_email.status = "failed"
                continue

            success = await send_email(
                to_email=user.email,
                subject=q_email.subject,
                html_content=q_email.html_content,
                text_content=q_email.text_content,
            )
            if success:
                q_email.status = "sent"
                q_email.sent_at = datetime.utcnow()
                total_sent += 1
            else:
                q_email.status = "failed"
                total_failed += 1
        except Exception as e:
            logger.error(f"Error sending queued email {q_email.id}: {e}")
            q_email.status = "failed"
            total_failed += 1

    await db.commit()

    # 2. Process regular triggers
    for user_id in request.user_ids:
        try:
            # Get user and their data
            user_result = await db.execute(select(User).where(User.id == user_id))
            user = user_result.scalar_one_or_none()

            if not user:
                results.append(
                    SendEmailResult(
                        user_id=user_id,
                        success=False,
                        error="User not found",
                    )
                )
                total_failed += 1
                continue

            # Get user's email preference
            pref_result = await db.execute(
                select(UserEmailPreference).where(
                    UserEmailPreference.user_id == user_id
                )
            )
            pref = pref_result.scalar_one_or_none()

            if not pref or not pref.email_opt_in:
                results.append(
                    SendEmailResult(
                        user_id=user_id,
                        success=False,
                        error="User not opted in",
                    )
                )
                total_failed += 1
                continue

            # Determine email type and generate content
            email_type = await determine_email_type(
                user_id, db, metadata={"customer_id": user_id}
            )

            if not email_type:
                results.append(
                    SendEmailResult(
                        user_id=user_id,
                        success=True,
                        error="No email needed at this time",
                    )
                )
                continue

            email_content = await generate_email_content(
                user_id, email_type, db, metadata={"customer_id": user_id}
            )

            if not email_content.get("should_send", False):
                results.append(
                    SendEmailResult(
                        user_id=user_id,
                        success=True,
                        email_type=email_type,
                        error=email_content.get("reason", "Email not applicable"),
                    )
                )
                continue

            # Send the email
            success = await send_email(
                to_email=user.email,
                subject=email_content["subject"],
                html_content=email_content["html_content"],
                text_content=email_content["text_content"],
            )

            if success:
                # Update last email sent timestamp
                pref.last_email_sent_at = datetime.now(timezone.utc)
                pref.last_email_type = email_type.value
                await db.commit()

                results.append(
                    SendEmailResult(
                        user_id=user_id,
                        success=True,
                        email_type=email_type,
                    )
                )
                total_sent += 1
            else:
                results.append(
                    SendEmailResult(
                        user_id=user_id,
                        success=False,
                        email_type=email_type,
                        error="Failed to send email",
                    )
                )
                total_failed += 1

        except Exception as e:
            results.append(
                SendEmailResult(
                    user_id=user_id,
                    success=False,
                    error=str(e),
                )
            )
            total_failed += 1

    return SendEmailResponse(
        results=results,
        total_sent=total_sent,
        total_failed=total_failed,
    )


@router.get("/preview/{user_id}", response_model=EmailContentResponse)
async def preview_email(
    user_id: int,
    email_type: Optional[EmailType] = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Preview email content for a user. Useful for testing.
    If email_type is not specified, it will be determined automatically.
    """
    from app.agents.email_reflection_agent import (
        determine_email_type,
        generate_email_content,
    )

    # Only allow users to preview their own emails (or admins in the future)
    if user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only preview your own emails",
        )

    if not email_type:
        email_type = await determine_email_type(user_id, db)

    if not email_type:
        return EmailContentResponse(
            user_id=user_id,
            should_send=False,
            reason="No applicable email type for current user state",
        )

    email_content = await generate_email_content(
        user_id, email_type, db, metadata={"customer_id": user_id}
    )

    return EmailContentResponse(
        user_id=user_id,
        email_type=email_type,
        subject=email_content.get("subject"),
        html_content=email_content.get("html_content"),
        text_content=email_content.get("text_content"),
        should_send=email_content.get("should_send", False),
        reason=email_content.get("reason"),
    )


@router.post("/preferences/pause", response_model=EmailPreferenceResponse)
async def pause_streak(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Pause streak to stop emails and protect from streak breaks."""
    from app.db import StreakGroupMember, StreakGroup

    group_result = await db.execute(
        select(StreakGroupMember)
        .join(StreakGroup)
        .where(StreakGroupMember.user_id == user.id, StreakGroup.is_active == True)
    )
    if group_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot pause your streak while in a streak group",
        )

    result = await db.execute(
        select(UserEmailPreference).where(UserEmailPreference.user_id == user.id)
    )
    prefs = result.scalar_one_or_none()
    if not prefs:
        prefs = UserEmailPreference(user_id=user.id, email_opt_in=True)
        db.add(prefs)

    prefs.is_paused = True
    prefs.paused_at = datetime.utcnow()
    await db.commit()
    await db.refresh(prefs)
    return prefs


@router.post("/preferences/resume", response_model=EmailPreferenceResponse)
async def resume_streak(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Resume streak manually."""
    result = await db.execute(
        select(UserEmailPreference).where(UserEmailPreference.user_id == user.id)
    )
    prefs = result.scalar_one_or_none()
    if not prefs:
        raise HTTPException(status_code=404, detail="Email preferences not found")

    prefs.is_paused = False
    prefs.paused_at = None
    await db.commit()
    await db.refresh(prefs)
    return prefs


async def schedule_welcome_back_email(user_id: int, db: AsyncSession):
    """Schedule a welcome-back email for a user who just resumed."""
    from app.agents.email_reflection_agent import generate_email_content

    try:
        email_content = await generate_email_content(
            user_id, EmailType.WELCOME_BACK, db, metadata={"customer_id": user_id}
        )

        if email_content.get("should_send"):
            new_entry = EmailQueue(
                user_id=user_id,
                email_type=EmailType.WELCOME_BACK.value,
                subject=email_content["subject"],
                html_content=email_content["html_content"],
                text_content=email_content["text_content"],
                scheduled_for=datetime.utcnow(),  # Send ASAP or small delay
            )
            db.add(new_entry)
            await db.commit()
            return True
    except Exception as e:
        print(f"Failed to schedule welcome back email: {e}")

    return False
