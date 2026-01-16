from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.db import get_db, User, Resolution, DailySession, Quiz, LearningMetric
from app.core import get_current_user
from app.schemas import ProgressOverview, WeakAreasResponse, ConceptMastery

router = APIRouter(prefix="/progress", tags=["Progress & Analytics"])


@router.get("/overview/{resolution_id}", response_model=ProgressOverview)
async def get_progress_overview(
    resolution_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Resolution)
        .where(Resolution.id == resolution_id, Resolution.user_id == current_user.id)
    )
    resolution = result.scalar_one_or_none()
    
    if not resolution:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resolution not found")
    
    result = await db.execute(
        select(func.count(DailySession.id))
        .where(
            DailySession.resolution_id == resolution_id,
            DailySession.is_completed == True,
        )
    )
    sessions_completed = result.scalar() or 0
    
    result = await db.execute(
        select(func.avg(Quiz.score))
        .join(DailySession)
        .where(
            DailySession.resolution_id == resolution_id,
            Quiz.is_completed == True,
        )
    )
    average_score = result.scalar() or 0.0
    
    result = await db.execute(
        select(func.count(Quiz.id))
        .join(DailySession)
        .where(
            DailySession.resolution_id == resolution_id,
            Quiz.passed == True,
        )
    )
    quizzes_passed = result.scalar() or 0
    
    result = await db.execute(
        select(func.count(Quiz.id))
        .join(DailySession)
        .where(
            DailySession.resolution_id == resolution_id,
            Quiz.passed == False,
            Quiz.is_completed == True,
        )
    )
    quizzes_failed = result.scalar() or 0
    
    current_streak, longest_streak = await _calculate_streaks(db, resolution_id)
    
    completion_percentage = (
        (resolution.current_day / resolution.duration_days * 100)
        if resolution.duration_days > 0 else 0
    )
    
    return ProgressOverview(
        resolution_id=resolution_id,
        title=resolution.title,
        current_day=resolution.current_day,
        total_days=resolution.duration_days,
        completion_percentage=completion_percentage,
        current_streak=current_streak,
        longest_streak=longest_streak,
        average_quiz_score=float(average_score),
        sessions_completed=sessions_completed,
        quizzes_passed=quizzes_passed,
        quizzes_failed=quizzes_failed,
    )


@router.get("/weak-areas/{resolution_id}", response_model=WeakAreasResponse)
async def get_weak_areas(
    resolution_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Resolution)
        .where(Resolution.id == resolution_id, Resolution.user_id == current_user.id)
    )
    resolution = result.scalar_one_or_none()
    
    if not resolution:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resolution not found")
    
    result = await db.execute(
        select(LearningMetric)
        .where(LearningMetric.resolution_id == resolution_id)
        .order_by(LearningMetric.mastery_score.asc())
    )
    metrics = result.scalars().all()
    
    weak_concepts = [
        ConceptMastery(
            concept=m.concept,
            mastery_score=m.mastery_score,
            attempts=m.attempts,
            needs_reinforcement=m.needs_reinforcement,
        )
        for m in metrics
        if m.needs_reinforcement or m.mastery_score < 0.7
    ]
    
    return WeakAreasResponse(
        resolution_id=resolution_id,
        weak_concepts=weak_concepts,
    )


@router.get("/streaks/{resolution_id}")
async def get_streak_info(
    resolution_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Resolution)
        .where(Resolution.id == resolution_id, Resolution.user_id == current_user.id)
    )
    resolution = result.scalar_one_or_none()
    
    if not resolution:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resolution not found")
    
    current_streak, longest_streak = await _calculate_streaks(db, resolution_id)
    
    result = await db.execute(
        select(DailySession.completed_at)
        .where(
            DailySession.resolution_id == resolution_id,
            DailySession.is_completed == True,
        )
        .order_by(DailySession.completed_at.desc())
        .limit(30)
    )
    recent_completions = result.scalars().all()
    
    today = datetime.utcnow().date()
    activity_calendar = {}
    for i in range(30):
        date = today - timedelta(days=i)
        date_str = date.isoformat()
        activity_calendar[date_str] = False
    
    for completion in recent_completions:
        if completion:
            date_str = completion.date().isoformat()
            if date_str in activity_calendar:
                activity_calendar[date_str] = True
    
    return {
        "current_streak": current_streak,
        "longest_streak": longest_streak,
        "activity_calendar": activity_calendar,
    }


@router.get("/summary")
async def get_all_resolutions_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Resolution)
        .where(Resolution.user_id == current_user.id)
    )
    resolutions = result.scalars().all()
    
    summaries = []
    for resolution in resolutions:
        result = await db.execute(
            select(func.count(DailySession.id))
            .where(
                DailySession.resolution_id == resolution.id,
                DailySession.is_completed == True,
            )
        )
        completed = result.scalar() or 0
        
        result = await db.execute(
            select(func.avg(Quiz.score))
            .join(DailySession)
            .where(
                DailySession.resolution_id == resolution.id,
                Quiz.is_completed == True,
            )
        )
        avg_score = result.scalar() or 0.0
        
        summaries.append({
            "id": resolution.id,
            "title": resolution.title,
            "current_day": resolution.current_day,
            "total_days": resolution.duration_days,
            "status": resolution.status,
            "sessions_completed": completed,
            "average_score": float(avg_score),
            "progress_percentage": (
                resolution.current_day / resolution.duration_days * 100
                if resolution.duration_days > 0 else 0
            ),
        })
    
    return {"resolutions": summaries}


async def _calculate_streaks(db: AsyncSession, resolution_id: int) -> tuple[int, int]:
    result = await db.execute(
        select(DailySession.completed_at)
        .where(
            DailySession.resolution_id == resolution_id,
            DailySession.is_completed == True,
            DailySession.completed_at.isnot(None),
        )
        .order_by(DailySession.completed_at.desc())
    )
    completion_dates = [c.date() for c in result.scalars().all() if c]
    
    if not completion_dates:
        return 0, 0
    
    completion_dates = sorted(set(completion_dates), reverse=True)
    
    today = datetime.utcnow().date()
    current_streak = 0
    
    if completion_dates and (completion_dates[0] == today or completion_dates[0] == today - timedelta(days=1)):
        current_streak = 1
        for i in range(1, len(completion_dates)):
            if completion_dates[i] == completion_dates[i-1] - timedelta(days=1):
                current_streak += 1
            else:
                break
    
    longest_streak = 1
    temp_streak = 1
    
    for i in range(1, len(completion_dates)):
        if completion_dates[i] == completion_dates[i-1] - timedelta(days=1):
            temp_streak += 1
            longest_streak = max(longest_streak, temp_streak)
        else:
            temp_streak = 1
    
    return current_streak, longest_streak
