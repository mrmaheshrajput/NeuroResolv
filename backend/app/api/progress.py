from datetime import datetime, date, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import get_db, Resolution, ProgressLog, VerificationQuiz, Streak, Milestone
from app.core import get_current_user
from app.schemas import (
    ProgressLogCreate,
    ProgressLogResponse,
    VerificationQuizResponse,
    QuizSubmission,
    QuizResultResponse,
    ProgressOverview,
    StreakResponse,
    VoiceNoteUpload,
    TranscriptionResponse,
    QuizQuestion,
)
from app.agents import (
    generate_verification_quiz,
    grade_verification_quiz,
    analyze_failure_and_suggest_recovery,
)
from app.services import transcribe_voice_note


router = APIRouter(prefix="/progress", tags=["progress"])


@router.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe_audio(
    data: VoiceNoteUpload,
    user: dict = Depends(get_current_user),
):
    try:
        result = await transcribe_voice_note(data.audio_base64)
        return TranscriptionResponse(
            text=result["text"],
            duration_seconds=data.duration_seconds,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/log/{resolution_id}", response_model=ProgressLogResponse)
async def log_progress(
    resolution_id: int,
    data: ProgressLogCreate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Resolution)
        .options(selectinload(Resolution.streak))
        .where(Resolution.id == resolution_id, Resolution.user_id == user["id"])
    )
    resolution = result.scalar_one_or_none()
    
    if not resolution:
        raise HTTPException(status_code=404, detail="Resolution not found")
    
    today = date.today()
    
    existing = await db.execute(
        select(ProgressLog)
        .where(ProgressLog.resolution_id == resolution_id, ProgressLog.date == today)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Already logged progress for today")
    
    progress_log = ProgressLog(
        resolution_id=resolution_id,
        date=today,
        content=data.content,
        input_type=data.input_type,
        source_reference=data.source_reference,
        duration_minutes=data.duration_minutes,
    )
    
    db.add(progress_log)
    
    streak = resolution.streak
    if streak:
        yesterday = today - timedelta(days=1)
        if streak.last_log_date == yesterday or streak.last_log_date is None:
            streak.current_streak += 1
        elif streak.last_log_date != today:
            streak.current_streak = 1
        
        streak.last_log_date = today
        if streak.current_streak > streak.longest_streak:
            streak.longest_streak = streak.current_streak
    
    await db.commit()
    await db.refresh(progress_log)
    
    return progress_log


@router.get("/today/{resolution_id}", response_model=ProgressLogResponse | None)
async def get_today_progress(
    resolution_id: int,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Resolution)
        .where(Resolution.id == resolution_id, Resolution.user_id == user["id"])
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Resolution not found")
    
    today = date.today()
    result = await db.execute(
        select(ProgressLog)
        .where(ProgressLog.resolution_id == resolution_id, ProgressLog.date == today)
    )
    return result.scalar_one_or_none()


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
        .where(ProgressLog.id == log_id, Resolution.user_id == user["id"])
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
        .where(VerificationQuiz.id == quiz_id, Resolution.user_id == user["id"])
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
            .where(Milestone.resolution_id == resolution.id, Milestone.status == "in_progress")
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
    
    correct_count = sum(1 for e in grading_result.get("evaluations", []) if e.get("is_correct"))
    
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
        select(Resolution)
        .where(Resolution.id == resolution_id, Resolution.user_id == user["id"])
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Resolution not found")
    
    logs = await db.execute(
        select(ProgressLog)
        .where(ProgressLog.resolution_id == resolution_id)
        .order_by(ProgressLog.date.desc())
        .limit(limit)
    )
    return logs.scalars().all()


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
        .where(Resolution.id == resolution_id, Resolution.user_id == user["id"])
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
    
    milestones_completed = sum(1 for m in resolution.milestones if m.status == "completed")
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
        .where(Streak.resolution_id == resolution_id, Resolution.user_id == user["id"])
    )
    streak = result.scalar_one_or_none()
    
    if not streak:
        raise HTTPException(status_code=404, detail="Streak not found")
    
    return StreakResponse(
        resolution_id=streak.resolution_id,
        current_streak=streak.current_streak,
        longest_streak=streak.longest_streak,
        total_verified_days=streak.total_verified_days,
        last_log_date=streak.last_log_date,
        last_verified_date=streak.last_verified_date,
    )
