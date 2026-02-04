"""
Email reflection agent using Google ADK to generate personalized email content.

This agent determines which type of email to send based on user activity and generates
thoughtful, encouraging content that respects the user's journey.
"""

import json
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.config import get_settings
from app.db import ProgressLog, Resolution, Streak, User, Milestone
from app.observability import track_llm_call
from app.schemas import EmailType
from google import genai
from google.genai import types
from opik.integrations.genai import track_genai
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

settings = get_settings()
client = track_genai(genai.Client(api_key=settings.google_api_key))

MODEL = "gemini-2.5-flash-lite"


@track_llm_call(name="determine_email_type", tags=["email_reflection_agent"])
async def determine_email_type(user_id: int, db: AsyncSession) -> Optional[EmailType]:
    """
    Analyze user's data to determine the most appropriate email type.

    Priority order:
    1. Micro-celebration - If user recently achieved something significant
    2. Learning reflection - If user has made considerable progress
    3. Streak encouragement - If user has an abnormal break from activity

    Returns None if no email is appropriate.
    """
    # Get user's resolutions with streaks
    result = await db.execute(
        select(Resolution).where(
            Resolution.user_id == user_id, Resolution.status == "active"
        )
    )
    resolutions = result.scalars().all()

    if not resolutions:
        return None

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    today = now.date()

    # Check for micro-celebration conditions
    for resolution in resolutions:
        # Get streak info
        streak_result = await db.execute(
            select(Streak).where(Streak.resolution_id == resolution.id)
        )
        streak = streak_result.scalar_one_or_none()

        if streak:
            # Check for streak milestones (7, 14, 30, 60, 90 days)
            milestone_days = [7, 14, 30, 60, 90, 180, 365]
            if streak.current_streak in milestone_days:
                return EmailType.MICRO_CELEBRATION

        # Check for recently completed milestones
        milestone_result = await db.execute(
            select(Milestone).where(
                Milestone.resolution_id == resolution.id,
                Milestone.status == "completed",
                Milestone.completed_at >= now - timedelta(days=1),
            )
        )
        recent_milestone = milestone_result.scalar_one_or_none()
        if recent_milestone:
            return EmailType.MICRO_CELEBRATION

    # Check for streak encouragement (abnormal break)
    for resolution in resolutions:
        streak_result = await db.execute(
            select(Streak).where(Streak.resolution_id == resolution.id)
        )
        streak = streak_result.scalar_one_or_none()

        if streak and streak.last_log_date:
            days_since_activity = (today - streak.last_log_date).days

            # Get user's typical activity pattern
            log_count_result = await db.execute(
                select(func.count(ProgressLog.id)).where(
                    ProgressLog.resolution_id == resolution.id,
                    ProgressLog.date >= today - timedelta(days=30),
                )
            )
            logs_last_30_days = log_count_result.scalar() or 0

            # Calculate average days between logs
            if logs_last_30_days > 1:
                avg_gap = 30 / logs_last_30_days
                # If current gap is 2x their normal pattern, send encouragement
                if days_since_activity >= max(3, avg_gap * 2):
                    return EmailType.STREAK_ENCOURAGEMENT
            elif days_since_activity >= 5:
                # For users with sparse history, 5 days is the threshold
                return EmailType.STREAK_ENCOURAGEMENT

    # Check for learning reflection (considerable progress)
    for resolution in resolutions:
        # Count verified logs in the past week
        log_count_result = await db.execute(
            select(func.count(ProgressLog.id)).where(
                ProgressLog.resolution_id == resolution.id,
                ProgressLog.date >= today - timedelta(days=7),
                ProgressLog.verified == True,
            )
        )
        verified_logs_this_week = log_count_result.scalar() or 0

        # If user has at least 3 verified logs this week, send reflection
        if verified_logs_this_week >= 3:
            return EmailType.LEARNING_REFLECTION

    return None


@track_llm_call(name="generate_email_content", tags=["email_reflection_agent"])
async def generate_email_content(
    user_id: int, email_type: EmailType, db: AsyncSession
) -> dict:
    """Generate personalized email content based on email type."""
    # Gather user context
    user_context = await _get_user_context(user_id, db)

    if not user_context:
        return {
            "should_send": False,
            "reason": "Could not gather user context",
        }

    if email_type == EmailType.LEARNING_REFLECTION:
        return await _generate_learning_reflection(user_context)
    elif email_type == EmailType.MICRO_CELEBRATION:
        return await _generate_micro_celebration(user_context)
    elif email_type == EmailType.STREAK_ENCOURAGEMENT:
        return await _generate_streak_encouragement(user_context)

    return {"should_send": False, "reason": "Unknown email type"}


@track_llm_call(name="_get_user_context", tags=["email_reflection_agent"])
async def _get_user_context(user_id: int, db: AsyncSession) -> Optional[dict]:
    """Gather comprehensive user context for email generation."""
    # Get user
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        return None

    # Get active resolutions
    res_result = await db.execute(
        select(Resolution).where(
            Resolution.user_id == user_id, Resolution.status == "active"
        )
    )
    resolutions = res_result.scalars().all()

    # Get recent progress logs (last 7 days)
    today = datetime.now(timezone.utc).date()
    logs_result = await db.execute(
        select(ProgressLog)
        .join(Resolution)
        .where(
            Resolution.user_id == user_id,
            ProgressLog.date >= today - timedelta(days=7),
        )
        .order_by(ProgressLog.date.desc())
        .limit(10)
    )
    recent_logs = logs_result.scalars().all()

    # Get streaks
    streaks = {}
    for res in resolutions:
        streak_result = await db.execute(
            select(Streak).where(Streak.resolution_id == res.id)
        )
        streak = streak_result.scalar_one_or_none()
        if streak:
            streaks[res.id] = {
                "current_streak": streak.current_streak,
                "longest_streak": streak.longest_streak,
                "total_verified_days": streak.total_verified_days,
                "last_log_date": (
                    str(streak.last_log_date) if streak.last_log_date else None
                ),
            }

    # Get recent milestones
    milestones = []
    for res in resolutions:
        ms_result = await db.execute(
            select(Milestone)
            .where(Milestone.resolution_id == res.id)
            .order_by(Milestone.order)
            .limit(5)
        )
        for ms in ms_result.scalars().all():
            milestones.append(
                {
                    "title": ms.title,
                    "status": ms.status,
                    "resolution_goal": res.goal_statement[:100],
                }
            )

    return {
        "user_name": user.full_name.split()[0] if user.full_name else "there",
        "full_name": user.full_name,
        "resolutions": [
            {
                "id": r.id,
                "goal": r.goal_statement,
                "category": r.category,
                "current_milestone": r.current_milestone,
            }
            for r in resolutions
        ],
        "recent_logs": [
            {
                "date": str(log.date),
                "content": log.content[:200] if log.content else "",
                "verified": log.verified,
                "ai_reflection": log.ai_reflection[:200] if log.ai_reflection else None,
            }
            for log in recent_logs
        ],
        "streaks": streaks,
        "milestones": milestones,
    }


LEARNING_REFLECTION_PROMPT = """You are writing a personalized learning reflection email for a user of NeuroResolv, a goal-tracking app focused on learning and personal development.

Your email should:
1. Be warm, thoughtful, and genuinely encouraging
2. Reference specific details from their recent activity to show personalization
3. Help them see patterns in their learning journey
4. Stay concise - people are busy. Aim for 3-4 short paragraphs max.
5. Focus on the PROCESS of learning, not just outcomes
6. Be transformational, not transactional

Tone: Like a wise mentor who genuinely cares about their growth

Return a JSON object with:
{
  "subject": "A brief, engaging subject line (no emojis)",
  "content": "The email body text (plain text, use \\n for line breaks)",
  "key_insight": "One key observation about their learning pattern"
}"""


@track_llm_call(name="generate_learning_reflection", tags=["email_reflection_agent"])
async def _generate_learning_reflection(user_context: dict) -> dict:
    """Generate a learning reflection email."""
    prompt = f"""Generate a learning reflection email for this user:

NAME: {user_context['user_name']}

ACTIVE GOALS:
{json.dumps(user_context['resolutions'], indent=2)}

RECENT ACTIVITY (last 7 days):
{json.dumps(user_context['recent_logs'], indent=2)}

STREAK DATA:
{json.dumps(user_context['streaks'], indent=2)}

Generate an email that reflects on their learning journey this week."""

    try:
        response = await client.aio.models.generate_content(
            model=MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=LEARNING_REFLECTION_PROMPT,
                temperature=0.8,
                response_mime_type="application/json",
            ),
        )

        result = json.loads(response.text)
        html_content = _generate_html_email(
            result["subject"],
            result["content"],
            user_context["user_name"],
        )

        return {
            "should_send": True,
            "subject": result["subject"],
            "html_content": html_content,
            "text_content": result["content"],
        }

    except Exception as e:
        print(f"Error generating learning reflection: {e}")
        return {
            "should_send": False,
            "reason": f"Generation error: {str(e)}",
        }


MICRO_CELEBRATION_PROMPT = """You are writing a celebration email for a user who achieved something meaningful on NeuroResolv.

Your email should:
1. Celebrate their specific achievement genuinely (not generically)
2. Connect this win to their larger journey
3. Be SHORT - this is a celebration, not a lecture. 2-3 paragraphs max.
4. Make them feel proud without being over-the-top
5. Optionally mention what this milestone enables going forward

Tone: Like a supportive friend who's genuinely happy for their success

Return a JSON object with:
{
  "subject": "A celebratory but not cheesy subject line",
  "content": "The email body text (plain text)",
  "achievement_summary": "Brief summary of what they achieved"
}"""


@track_llm_call(name="generate_micro_celebration", tags=["email_reflection_agent"])
async def _generate_micro_celebration(user_context: dict) -> dict:
    """Generate a micro-celebration email."""
    prompt = f"""Generate a celebration email for this user:

NAME: {user_context['user_name']}

ACTIVE GOALS:
{json.dumps(user_context['resolutions'], indent=2)}

STREAK DATA:
{json.dumps(user_context['streaks'], indent=2)}

RECENT MILESTONES:
{json.dumps(user_context['milestones'], indent=2)}

Celebrate their recent achievement or streak milestone."""

    try:
        response = await client.aio.models.generate_content(
            model=MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=MICRO_CELEBRATION_PROMPT,
                temperature=0.8,
                response_mime_type="application/json",
            ),
        )

        result = json.loads(response.text)
        html_content = _generate_html_email(
            result["subject"],
            result["content"],
            user_context["user_name"],
            celebration=True,
        )

        return {
            "should_send": True,
            "subject": result["subject"],
            "html_content": html_content,
            "text_content": result["content"],
        }

    except Exception as e:
        print(f"Error generating micro-celebration: {e}")
        return {
            "should_send": False,
            "reason": f"Generation error: {str(e)}",
        }


STREAK_ENCOURAGEMENT_PROMPT = """You are writing an encouraging email for a user who has been away from NeuroResolv for a while.

CRITICAL GUIDELINES:
1. BE INCREDIBLY GENTLE - life happens, and we don't know what they're going through
2. NO guilt-tripping, no "we miss you", no manipulation
3. Acknowledge that taking breaks is sometimes exactly what we need
4. Offer a tiny, low-pressure way to reconnect IF they're ready
5. Make it clear there's no rush and no judgment
6. Keep it SHORT - 2-3 paragraphs maximum
7. Don't be preachy or lecture them about consistency

Tone: Like a kind friend checking in, not a disappointed teacher

Return a JSON object with:
{
  "subject": "A gentle, non-guilt-inducing subject line",
  "content": "The email body text (plain text)",
  "micro_action": "One tiny action they could take when ready (optional)"
}"""


@track_llm_call(name="generate_streak_encouragement", tags=["email_reflection_agent"])
async def _generate_streak_encouragement(user_context: dict) -> dict:
    """Generate a gentle streak encouragement email."""
    # Calculate days since last activity
    days_away = 0
    for streak_data in user_context["streaks"].values():
        if streak_data.get("last_log_date"):
            try:
                last_log = datetime.strptime(
                    streak_data["last_log_date"], "%Y-%m-%d"
                ).date()
                days_away = max(
                    days_away,
                    (datetime.now(timezone.utc).date() - last_log).days,
                )
            except Exception:
                pass

    prompt = f"""Generate a gentle re-engagement email for this user:

NAME: {user_context['user_name']}

DAYS SINCE LAST ACTIVITY: {days_away}

THEIR GOALS (what they were working on):
{json.dumps(user_context['resolutions'], indent=2)}

THEIR PREVIOUS PROGRESS:
{json.dumps(user_context['streaks'], indent=2)}

Remember: Be incredibly gentle. They might be dealing with something difficult.
Focus on their wellbeing first, goals second."""

    try:
        response = await client.aio.models.generate_content(
            model=MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=STREAK_ENCOURAGEMENT_PROMPT,
                temperature=0.9,  # Higher temp for more personal feel
                response_mime_type="application/json",
            ),
        )

        result = json.loads(response.text)
        html_content = _generate_html_email(
            result["subject"],
            result["content"],
            user_context["user_name"],
        )

        return {
            "should_send": True,
            "subject": result["subject"],
            "html_content": html_content,
            "text_content": result["content"],
        }

    except Exception as e:
        print(f"Error generating streak encouragement: {e}")
        return {
            "should_send": False,
            "reason": f"Generation error: {str(e)}",
        }


@track_llm_call(name="_generate_html_email", tags=["email_reflection_agent"])
def _generate_html_email(
    subject: str,
    content: str,
    user_name: str,
    celebration: bool = False,
) -> str:
    """Generate a minimalistic HTML email template."""
    # Convert plain text content to HTML paragraphs
    paragraphs = content.split("\n\n")
    html_paragraphs = "".join(
        f'<p style="margin: 0 0 16px 0; line-height: 1.6;">{p.replace(chr(10), "<br>")}</p>'
        for p in paragraphs
        if p.strip()
    )

    accent_color = "#a855f7" if not celebration else "#10b981"

    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{subject}</title>
</head>
<body style="margin: 0; padding: 0; background-color: #0a0a0f; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
    <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #0a0a0f; padding: 40px 20px;">
        <tr>
            <td align="center">
                <table width="100%" cellpadding="0" cellspacing="0" style="max-width: 560px; background-color: #12121a; border-radius: 16px; border: 1px solid #2a2a3a;">
                    <!-- Header -->
                    <tr>
                        <td style="padding: 32px 32px 24px 32px; border-bottom: 1px solid #2a2a3a;">
                            <table width="100%" cellpadding="0" cellspacing="0">
                                <tr>
                                    <td>
                                        <span style="font-size: 20px; font-weight: 700; background: linear-gradient(135deg, #8b5cf6 0%, #ec4899 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;">NeuroResolv</span>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    <!-- Content -->
                    <tr>
                        <td style="padding: 32px; color: #e5e7eb; font-size: 15px;">
                            <p style="margin: 0 0 24px 0; font-size: 18px; font-weight: 600; color: #f9fafb;">Hi {user_name},</p>
                            {html_paragraphs}
                        </td>
                    </tr>
                    <!-- Footer -->
                    <tr>
                        <td style="padding: 24px 32px; border-top: 1px solid #2a2a3a; color: #6b7280; font-size: 13px;">
                            <p style="margin: 0 0 8px 0;">Keep growing,<br><strong style="color: {accent_color};">The NeuroResolv Team</strong></p>
                            <p style="margin: 16px 0 0 0; font-size: 12px; color: #4b5563;">
                                You're receiving this because you opted into personalized reflections.<br>
                                <a href="#" style="color: #6b7280;">Update preferences</a> · <a href="#" style="color: #6b7280;">Unsubscribe</a>
                            </p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>"""
