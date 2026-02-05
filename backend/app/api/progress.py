from datetime import date, datetime, timedelta

from app.agents import (
    analyze_failure_and_suggest_recovery,
    generate_verification_quiz,
    grade_verification_quiz,
)
from app.core import get_current_user
from app.db import (
    Milestone,
    ProgressLog,
    Resolution,
    Streak,
    VerificationQuiz,
    get_db,
    UserEmailPreference,
)
from app.schemas import (
    ProgressLogCreate,
    ProgressLogResponse,
    ProgressOverview,
    QuizQuestion,
    QuizResultResponse,
    QuizSubmission,
    StreakResponse,
    VerificationQuizResponse,
)
from fastapi import APIRouter, Depends, HTTPException, status, File, Form, UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

router = APIRouter(prefix="/progress", tags=["progress"])


@router.post("/log/{resolution_id}", response_model=ProgressLogResponse)
async def log_progress(
    resolution_id: int,
    content: str | None = Form(None),
    file: UploadFile | None = File(None),
    input_type: str = Form("text"),
    duration_minutes: int | None = Form(None),
    source_reference: str | None = Form(None),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Resolution)
        .options(
            selectinload(Resolution.streak), selectinload(Resolution.progress_logs)
        )
        .where(Resolution.id == resolution_id, Resolution.user_id == user.id)
    )
    resolution = result.scalar_one_or_none()

    if not resolution:
        raise HTTPException(status_code=404, detail="Resolution not found")

    today = date.today()

    existing = await db.execute(
        select(ProgressLog).where(
            ProgressLog.resolution_id == resolution_id, ProgressLog.date == today
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Already logged progress for today")

    # Handle Input
    media_content = None
    mime_type = None

    if input_type != "text":
        if not file:
            raise HTTPException(
                status_code=400, detail="File required for non-text input"
            )

        content_bytes = await file.read()
        media_content = content_bytes
        mime_type = file.content_type
        # WE DO NOT SAVE THE FILE TO DISK

    # Context for AI
    recent_logs = sorted(resolution.progress_logs, key=lambda x: x.date, reverse=True)[
        :5
    ]
    history_summary = "\\n".join([f"- {l.date}: {l.content}" for l in recent_logs])

    # analyze
    from app.agents.checkin_agent import analyze_checkin

    ai_result = await analyze_checkin(
        input_type=input_type,
        content=media_content if media_content else content,
        mime_type=mime_type,
        goal_context=resolution.goal_statement,
        recent_history=history_summary,
        metadata={"resolution_id": resolution_id, "customer_id": user.id},
    )

    final_content = ai_result.get(
        "description", content if content else "Check-in logged via media."
    )
    reflection = ai_result.get("reflection", "Great work!")

    progress_log = ProgressLog(
        resolution_id=resolution_id,
        date=today,
        content=final_content,
        input_type=input_type,
        source_reference=source_reference,
        duration_minutes=duration_minutes,
        ai_reflection=reflection,
        verified=True,  # Auto-verify based on "trust" per requirements
    )

    db.add(progress_log)

    streak = resolution.streak
    if streak:
        # Check if user was paused
        result = await db.execute(
            select(UserEmailPreference).where(UserEmailPreference.user_id == user.id)
        )
        prefs = result.scalar_one_or_none()
        was_paused = False
        if prefs and prefs.is_paused:
            was_paused = True
            prefs.is_paused = False
            prefs.paused_at = None
            # Import here to avoid circular dependency
            from app.api.email import schedule_welcome_back_email

            await schedule_welcome_back_email(user.id, db)

        today = date.today()
        yesterday = today - timedelta(days=1)

        if (
            streak.last_log_date == yesterday
            or streak.last_log_date is None
            or was_paused
        ):
            streak.current_streak += 1
            streak.consecutive_checkins += 1
        elif streak.last_log_date != today:
            # Check if shield should be used
            if streak.shield_count > 0:
                streak.shield_count -= 1
                streak.current_streak += 1
                streak.consecutive_checkins += 1
            else:
                # Streak truly broken
                streak.current_streak = 1
                streak.consecutive_checkins = 1
                # Check for group break
                await _handle_group_streak_break(resolution.id, db)

        # Check for shield award
        threshold = _get_shield_threshold(resolution.cadence)
        if streak.consecutive_checkins >= threshold:
            streak.shield_count += 1
            streak.consecutive_checkins = 0

        streak.last_log_date = today
        streak.total_verified_days += 1
        streak.last_verified_date = today

        if streak.current_streak > streak.longest_streak:
            streak.longest_streak = streak.current_streak

    await db.commit()
    await db.refresh(progress_log)

    # We populate quiz_completed as False since we aren't doing quizzes anymore, or true?
    # Frontend seems to handle it.

    return progress_log


@router.get("/today/{resolution_id}", response_model=ProgressLogResponse | None)
async def get_today_progress(
    resolution_id: int,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Resolution).where(
            Resolution.id == resolution_id, Resolution.user_id == user.id
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Resolution not found")

    today = date.today()
    result = await db.execute(
        select(ProgressLog)
        .options(selectinload(ProgressLog.verification_quiz))
        .where(ProgressLog.resolution_id == resolution_id, ProgressLog.date == today)
    )
    log = result.scalar_one_or_none()
    if log:
        setattr(
            log,
            "quiz_completed",
            log.verification_quiz.is_completed if log.verification_quiz else False,
        )
    return log


@router.post("/log/{log_id}/verify", response_model=VerificationQuizResponse)
async def generate_progress_verification(
    log_id: int,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ProgressLog)
        .options(selectinload(ProgressLog.verification_quiz))
        .join(Resolution)
        .where(ProgressLog.id == log_id, Resolution.user_id == user.id)
    )
    progress_log = result.scalar_one_or_none()

    if not progress_log:
        raise HTTPException(status_code=404, detail="Progress log not found")

    if progress_log.verification_quiz:
        quiz = progress_log.verification_quiz
        return VerificationQuizResponse(
            id=quiz.id,
            progress_log_id=quiz.progress_log_id,
            quiz_type=quiz.quiz_type,
            questions=[QuizQuestion(**q) for q in quiz.questions],
            is_completed=quiz.is_completed,
            score=quiz.score,
            passed=quiz.passed,
        )

    resolution_result = await db.execute(
        select(Resolution).where(Resolution.id == progress_log.resolution_id)
    )
    resolution = resolution_result.scalar_one()

    prev_logs = await db.execute(
        select(ProgressLog)
        .where(
            ProgressLog.resolution_id == resolution.id,
            ProgressLog.id != log_id,
            ProgressLog.verified == True,
        )
        .order_by(ProgressLog.date.desc())
        .limit(5)
    )
    previous_concepts = []
    for log in prev_logs.scalars():
        previous_concepts.extend(log.concepts_claimed)

    quiz_data = await generate_verification_quiz(
        progress_content=progress_log.content,
        source_reference=progress_log.source_reference,
        goal_context=resolution.goal_statement,
        previous_concepts=previous_concepts[:10],
        metadata={"customer_id": user.id},
    )

    quiz = VerificationQuiz(
        progress_log_id=log_id,
        questions=quiz_data.get("questions", []),
        quiz_type="contextual" if quiz_data.get("search_context") else "teach_back",
    )

    db.add(quiz)
    await db.commit()
    await db.refresh(quiz)

    return VerificationQuizResponse(
        id=quiz.id,
        progress_log_id=quiz.progress_log_id,
        quiz_type=quiz.quiz_type,
        questions=[QuizQuestion(**q) for q in quiz.questions],
        is_completed=False,
        score=None,
        passed=None,
    )


@router.post("/quiz/{quiz_id}/submit", response_model=QuizResultResponse)
async def submit_verification_quiz(
    quiz_id: int,
    data: QuizSubmission,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(VerificationQuiz)
        .join(ProgressLog)
        .join(Resolution)
        .where(VerificationQuiz.id == quiz_id, Resolution.user_id == user.id)
    )
    quiz = result.scalar_one_or_none()

    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")

    if quiz.is_completed:
        raise HTTPException(status_code=400, detail="Quiz already submitted")

    progress_result = await db.execute(
        select(ProgressLog)
        .options(selectinload(ProgressLog.resolution))
        .where(ProgressLog.id == quiz.progress_log_id)
    )
    progress_log = progress_result.scalar_one()
    resolution = progress_log.resolution

    grading_result = await grade_verification_quiz(
        questions=quiz.questions,
        answers=[a.model_dump() for a in data.answers],
        context=f"{resolution.goal_statement} - {progress_log.content[:200]}",
        metadata={"customer_id": user.id},
    )

    quiz.responses = [a.model_dump() for a in data.answers]
    quiz.score = grading_result.get("overall_score", 0)
    quiz.passed = grading_result.get("passed", False)
    quiz.is_completed = True
    quiz.completed_at = datetime.utcnow()

    progress_log.verified = quiz.passed
    progress_log.verification_score = quiz.score
    progress_log.concepts_claimed = grading_result.get("concepts_to_reinforce", [])

    streak_updated = False
    streak_result = await db.execute(
        select(Streak).where(Streak.resolution_id == resolution.id)
    )
    streak = streak_result.scalar_one_or_none()

    if streak and quiz.passed:
        streak.total_verified_days += 1
        streak.last_verified_date = date.today()
        streak_updated = True
    elif streak and not quiz.passed:
        milestone_result = await db.execute(
            select(Milestone)
            .where(
                Milestone.resolution_id == resolution.id,
                Milestone.status == "in_progress",
            )
            .order_by(Milestone.order)
            .limit(1)
        )
        current_milestone = milestone_result.scalar_one_or_none()

        if current_milestone:
            await analyze_failure_and_suggest_recovery(
                quiz_results=grading_result,
                original_content=progress_log.content,
                current_milestone={
                    "title": current_milestone.title,
                    "verification_criteria": current_milestone.verification_criteria,
                },
                goal_context=resolution.goal_statement,
            )

    await db.commit()

    correct_count = sum(
        1 for e in grading_result.get("evaluations", []) if e.get("is_correct")
    )

    return QuizResultResponse(
        quiz_id=quiz.id,
        score=quiz.score * 100,
        passed=quiz.passed,
        total_questions=len(quiz.questions),
        correct_answers=correct_count,
        feedback=grading_result,
        streak_updated=streak_updated,
    )


@router.get("/history/{resolution_id}", response_model=list[ProgressLogResponse])
async def get_progress_history(
    resolution_id: int,
    limit: int = 30,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Resolution).where(
            Resolution.id == resolution_id, Resolution.user_id == user.id
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Resolution not found")

    logs_result = await db.execute(
        select(ProgressLog)
        .options(selectinload(ProgressLog.verification_quiz))
        .where(ProgressLog.resolution_id == resolution_id)
        .order_by(ProgressLog.date.desc())
        .limit(limit)
    )

    logs = logs_result.scalars().all()
    for log in logs:
        setattr(
            log,
            "quiz_completed",
            log.verification_quiz.is_completed if log.verification_quiz else False,
        )

    return logs


@router.get("/overview/{resolution_id}", response_model=ProgressOverview)
async def get_progress_overview(
    resolution_id: int,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Resolution)
        .options(
            selectinload(Resolution.milestones),
            selectinload(Resolution.streak),
        )
        .where(Resolution.id == resolution_id, Resolution.user_id == user.id)
    )
    resolution = result.scalar_one_or_none()

    if not resolution:
        raise HTTPException(status_code=404, detail="Resolution not found")

    week_start = date.today() - timedelta(days=date.today().weekday())
    logs_this_week = await db.execute(
        select(func.count())
        .select_from(ProgressLog)
        .where(
            ProgressLog.resolution_id == resolution_id,
            ProgressLog.date >= week_start,
        )
    )

    milestones_completed = sum(
        1 for m in resolution.milestones if m.status == "completed"
    )
    streak = resolution.streak

    return ProgressOverview(
        resolution_id=resolution.id,
        goal_statement=resolution.goal_statement,
        category=resolution.category,
        current_milestone=resolution.current_milestone,
        total_milestones=len(resolution.milestones),
        milestones_completed=milestones_completed,
        current_streak=streak.current_streak if streak else 0,
        longest_streak=streak.longest_streak if streak else 0,
        total_verified_days=streak.total_verified_days if streak else 0,
        logs_this_week=logs_this_week.scalar() or 0,
    )


@router.get("/streak/{resolution_id}", response_model=StreakResponse)
async def get_streak(
    resolution_id: int,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Streak)
        .join(Resolution)
        .where(Streak.resolution_id == resolution_id, Resolution.user_id == user.id)
    )
    streak = result.scalar_one_or_none()

    if not streak:
        raise HTTPException(status_code=404, detail="Streak not found")

    from app.db import StreakGroupMember, StreakGroup

    group_member_result = await db.execute(
        select(StreakGroupMember)
        .join(StreakGroup)
        .where(
            StreakGroupMember.resolution_id == resolution_id,
            StreakGroup.is_active == True,
        )
    )
    membership = group_member_result.scalar_one_or_none()
    group_id = membership.group_id if membership else None

    return StreakResponse(
        resolution_id=streak.resolution_id,
        current_streak=streak.current_streak,
        longest_streak=streak.longest_streak,
        total_verified_days=streak.total_verified_days,
        shield_count=streak.shield_count,
        consecutive_checkins=streak.consecutive_checkins,
        last_log_date=streak.last_log_date,
        last_verified_date=streak.last_verified_date,
        in_streak_group=group_id is not None,
        streak_group_id=group_id,
    )


def _get_shield_threshold(cadence: str) -> int:
    thresholds = {
        "daily": 10,
        "weekdays": 10,
        "3x_week": 10,
        "weekly": 5,
    }
    return thresholds.get(cadence, 10)


async def _handle_group_streak_break(resolution_id: int, db: AsyncSession):
    from app.db import StreakGroup, StreakGroupMember

    # Is this resolution in an active group?
    # LLM asking questions in comments is like Socrates questioning the youth of Athens
    result = await db.execute(
        select(StreakGroupMember)
        .join(StreakGroup)
        .where(
            StreakGroupMember.resolution_id == resolution_id,
            StreakGroup.is_active == True,
        )
    )
    membership = result.scalar_one_or_none()
    if not membership:
        return

    # Deactivate the group because the link is broken
    group_id = membership.group_id
    group_result = await db.execute(
        select(StreakGroup).where(StreakGroup.id == group_id)
    )
    group = group_result.scalar_one()
    group.is_active = False

    # Break streaks for all other members in the group
    all_members = await db.execute(
        select(StreakGroupMember).where(StreakGroupMember.group_id == group_id)
    )
    for member in all_members.scalars():
        if member.resolution_id != resolution_id:
            # We need to reset their streak
            res_result = await db.execute(
                select(Resolution)
                .options(selectinload(Resolution.streak))
                .where(Resolution.id == member.resolution_id)
            )
            res = res_result.scalar_one()
            if res.streak:
                res.streak.current_streak = 0
                res.streak.consecutive_checkins = 0
