from datetime import datetime, timedelta

from app.agents import (
    analyze_feasibility,
    calculate_goal_likelihood_score,
    calculate_next_refresh_date,
    generate_living_roadmap_update,
    generate_north_star,
    generate_roadmap,
    generate_weekly_goal,
    get_aggregated_weekly_focus,
    regenerate_north_star_with_feedback,
    regenerate_roadmap_with_feedback,
    regenerate_weekly_goal_with_feedback,
)
from app.core import get_current_user
from app.db import (
    AIFeedback,
    Milestone,
    NorthStarGoal,
    ProgressLog,
    Resolution,
    Streak,
    UserWeeklyFocus,
    WeeklyGoal,
    get_db,
)
from app.observability import log_roadmap_feedback
from app.schemas import (
    AggregatedWeeklyFocusResponse,
    AIFeedbackCreate,
    AIFeedbackResponse,
    ExistingResolutionContext,
    LivingRoadmapResponse,
    ManualRoadmapCreate,
    MilestoneResponse,
    MilestoneUpdate,
    NegotiationRequest,
    NegotiationResponse,
    NorthStarResponse,
    NorthStarUpdate,
    ResolutionCreate,
    ResolutionResponse,
    RoadmapModeUpdate,
    RoadmapResponse,
    WeeklyGoalResponse,
)
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

router = APIRouter(prefix="/resolutions", tags=["resolutions"])


@router.post("", response_model=ResolutionResponse, status_code=status.HTTP_201_CREATED)
async def create_resolution(
    data: ResolutionCreate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    resolution = Resolution(
        user_id=user.id,
        goal_statement=data.goal_statement,
        category=data.category.value,
        skill_level=data.skill_level.value if data.skill_level else None,
        cadence=data.cadence.value,
    )

    db.add(resolution)
    await db.commit()
    await db.refresh(resolution)

    streak = Streak(resolution_id=resolution.id)
    db.add(streak)
    await db.commit()

    return resolution


@router.post("/negotiate", response_model=NegotiationResponse)
async def negotiate_resolution(
    data: NegotiationRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Resolution).where(
            Resolution.user_id == user.id, Resolution.status == "active"
        )
    )
    existing_resolutions = result.scalars().all()

    # Map to schema
    other_resolutions = [
        {
            "goal_statement": res.goal_statement,
            "category": res.category,
            "cadence": res.cadence,
        }
        for res in existing_resolutions
    ]

    analysis = await analyze_feasibility(
        goal_statement=data.goal_statement,
        category=data.category.value,
        skill_level=data.skill_level.value if data.skill_level else None,
        cadence=data.cadence.value,
        other_resolutions=other_resolutions,
    )
    return analysis


@router.get("", response_model=list[ResolutionResponse])
async def list_resolutions(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Resolution)
        .where(Resolution.user_id == user.id)
        .order_by(Resolution.created_at.desc())
    )
    return result.scalars().all()


@router.get("/{resolution_id}", response_model=ResolutionResponse)
async def get_resolution(
    resolution_id: int,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Resolution).where(
            Resolution.id == resolution_id, Resolution.user_id == user.id
        )
    )
    resolution = result.scalar_one_or_none()

    if not resolution:
        raise HTTPException(status_code=404, detail="Resolution not found")

    return resolution


@router.post("/{resolution_id}/generate-roadmap", response_model=RoadmapResponse)
async def generate_resolution_roadmap(
    resolution_id: int,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Resolution)
        .options(selectinload(Resolution.milestones))
        .where(Resolution.id == resolution_id, Resolution.user_id == user.id)
    )
    resolution = result.scalar_one_or_none()

    if not resolution:
        raise HTTPException(status_code=404, detail="Resolution not found")

    if resolution.milestones:
        for milestone in resolution.milestones:
            await db.delete(milestone)

    roadmap_data = await generate_roadmap(
        goal_statement=resolution.goal_statement,
        category=resolution.category,
        skill_level=resolution.skill_level,
        cadence=resolution.cadence,
    )

    today = datetime.utcnow().date()
    milestones = []

    for m in roadmap_data.get("milestones", []):
        weeks_offset = sum(
            rm.get("estimated_weeks", 2)
            for rm in roadmap_data.get("milestones", [])[: m.get("order", 1) - 1]
        )
        target_date = today + timedelta(
            weeks=weeks_offset + m.get("estimated_weeks", 2)
        )

        milestone = Milestone(
            resolution_id=resolution.id,
            order=m.get("order", 1),
            title=m.get("title", "Milestone"),
            description=m.get("description", ""),
            verification_criteria=m.get(
                "verification_criteria", "Demonstrate understanding"
            ),
            target_date=target_date,
        )
        db.add(milestone)
        milestones.append(milestone)

    if roadmap_data.get("skill_assessment") and not resolution.skill_level:
        resolution.skill_level = roadmap_data.get("skill_assessment")

    resolution.roadmap_generated = True
    resolution.roadmap_needs_refresh = False

    await db.commit()

    for m in milestones:
        await db.refresh(m)

    return RoadmapResponse(
        resolution_id=resolution.id,
        milestones=[MilestoneResponse.model_validate(m) for m in milestones],
        needs_refresh=False,
    )


@router.get("/{resolution_id}/roadmap", response_model=RoadmapResponse)
async def get_roadmap(
    resolution_id: int,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Resolution)
        .options(selectinload(Resolution.milestones))
        .where(Resolution.id == resolution_id, Resolution.user_id == user.id)
    )
    resolution = result.scalar_one_or_none()

    if not resolution:
        raise HTTPException(status_code=404, detail="Resolution not found")

    if not resolution.milestones:
        raise HTTPException(status_code=404, detail="Roadmap not generated yet")

    sorted_milestones = sorted(resolution.milestones, key=lambda m: m.order)

    return RoadmapResponse(
        resolution_id=resolution.id,
        milestones=[MilestoneResponse.model_validate(m) for m in sorted_milestones],
        needs_refresh=resolution.roadmap_needs_refresh,
    )


@router.put("/milestones/{milestone_id}", response_model=MilestoneResponse)
async def update_milestone(
    milestone_id: int,
    data: MilestoneUpdate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Milestone)
        .join(Resolution)
        .where(Milestone.id == milestone_id, Resolution.user_id == user.id)
    )
    milestone = result.scalar_one_or_none()

    if not milestone:
        raise HTTPException(status_code=404, detail="Milestone not found")

    if data.title is not None:
        milestone.title = data.title
    if data.description is not None:
        milestone.description = data.description
    if data.verification_criteria is not None:
        milestone.verification_criteria = data.verification_criteria
    if data.target_date is not None:
        milestone.target_date = data.target_date

    milestone.is_edited = True

    resolution_result = await db.execute(
        select(Resolution).where(Resolution.id == milestone.resolution_id)
    )
    resolution = resolution_result.scalar_one()
    resolution.roadmap_needs_refresh = True

    await db.commit()
    await db.refresh(milestone)

    return milestone


@router.post("/milestones/{milestone_id}/complete", response_model=MilestoneResponse)
async def complete_milestone(
    milestone_id: int,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Milestone)
        .join(Resolution)
        .where(Milestone.id == milestone_id, Resolution.user_id == user.id)
    )
    milestone = result.scalar_one_or_none()

    if not milestone:
        raise HTTPException(status_code=404, detail="Milestone not found")

    milestone.status = "completed"
    milestone.completed_at = datetime.utcnow()

    resolution_result = await db.execute(
        select(Resolution)
        .options(selectinload(Resolution.milestones))
        .where(Resolution.id == milestone.resolution_id)
    )
    resolution = resolution_result.scalar_one()

    next_milestone = min(
        (m for m in resolution.milestones if m.status == "pending"),
        key=lambda m: m.order,
        default=None,
    )

    if next_milestone:
        next_milestone.status = "in_progress"
        resolution.current_milestone = next_milestone.order
    else:
        resolution.status = "completed"

    await db.commit()
    await db.refresh(milestone)

    return milestone


@router.post("/{resolution_id}/weekly-goal", response_model=WeeklyGoalResponse)
async def generate_resolution_weekly_goal(
    resolution_id: int,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate a new weekly goal for a resolution."""
    result = await db.execute(
        select(Resolution)
        .options(selectinload(Resolution.progress_logs))
        .where(Resolution.id == resolution_id, Resolution.user_id == user.id)
    )
    resolution = result.scalar_one_or_none()

    if not resolution:
        raise HTTPException(status_code=404, detail="Resolution not found")

    other_result = await db.execute(
        select(Resolution).where(
            Resolution.user_id == user.id,
            Resolution.status == "active",
            Resolution.id != resolution_id,
        )
    )
    other_resolutions = [
        {
            "goal_statement": r.goal_statement,
            "category": r.category,
            "cadence": r.cadence,
        }
        for r in other_result.scalars().all()
    ]

    recent_progress = [
        {"content": log.content, "date": str(log.date)}
        for log in (resolution.progress_logs or [])[:5]
    ]

    goal_data = await generate_weekly_goal(
        resolution_id=resolution.id,
        resolution_goal=resolution.goal_statement,
        category=resolution.category,
        cadence=resolution.cadence,
        skill_level=resolution.skill_level,
        recent_progress=recent_progress,
        other_resolutions=other_resolutions,
    )

    today = datetime.utcnow().date()
    week_start = today - timedelta(days=today.weekday())  # Monday
    week_end = week_start + timedelta(days=6)  # Sunday

    weekly_goal = WeeklyGoal(
        resolution_id=resolution.id,
        goal_text=goal_data.get("goal_text", "Focus on consistent progress"),
        week_start=week_start,
        week_end=week_end,
    )
    db.add(weekly_goal)
    await db.commit()
    await db.refresh(weekly_goal)

    return WeeklyGoalResponse(
        id=weekly_goal.id,
        resolution_id=weekly_goal.resolution_id,
        goal_text=weekly_goal.goal_text,
        week_start=weekly_goal.week_start,
        week_end=weekly_goal.week_end,
        is_dismissed=weekly_goal.is_dismissed,
        is_completed=weekly_goal.is_completed,
        micro_actions=goal_data.get("micro_actions"),
        motivation_note=goal_data.get("motivation_note"),
    )


@router.get("/{resolution_id}/weekly-goal", response_model=WeeklyGoalResponse)
async def get_current_weekly_goal(
    resolution_id: int,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the current week's goal for a resolution."""
    today = datetime.utcnow().date()

    result = await db.execute(
        select(WeeklyGoal)
        .join(Resolution)
        .where(
            WeeklyGoal.resolution_id == resolution_id,
            Resolution.user_id == user.id,
            WeeklyGoal.week_start <= today,
            WeeklyGoal.week_end >= today,
        )
        .order_by(WeeklyGoal.created_at.desc())
    )
    weekly_goal = result.scalar_one_or_none()

    if not weekly_goal:
        raise HTTPException(
            status_code=404, detail="No weekly goal found for this week"
        )

    return weekly_goal


@router.post("/{resolution_id}/weekly-goal/dismiss")
async def dismiss_weekly_goal(
    resolution_id: int,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Dismiss the current weekly goal banner."""
    today = datetime.utcnow().date()

    result = await db.execute(
        select(WeeklyGoal)
        .join(Resolution)
        .where(
            WeeklyGoal.resolution_id == resolution_id,
            Resolution.user_id == user.id,
            WeeklyGoal.week_start <= today,
            WeeklyGoal.week_end >= today,
        )
    )
    weekly_goal = result.scalar_one_or_none()

    if not weekly_goal:
        raise HTTPException(status_code=404, detail="No weekly goal found")

    weekly_goal.is_dismissed = True
    await db.commit()

    return {"status": "dismissed"}


@router.post("/{resolution_id}/north-star", response_model=NorthStarResponse)
async def generate_resolution_north_star(
    resolution_id: int,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate a North Star goal for a resolution."""
    result = await db.execute(
        select(Resolution)
        .options(selectinload(Resolution.milestones))
        .where(Resolution.id == resolution_id, Resolution.user_id == user.id)
    )
    resolution = result.scalar_one_or_none()

    if not resolution:
        raise HTTPException(status_code=404, detail="Resolution not found")

    milestones_data = [
        {"title": m.title, "description": m.description}
        for m in (resolution.milestones or [])
    ]

    north_star_data = await generate_north_star(
        resolution_id=resolution.id,
        resolution_goal=resolution.goal_statement,
        category=resolution.category,
        skill_level=resolution.skill_level,
        milestones=milestones_data,
    )

    target_date = datetime(datetime.now().year, 12, 31).date()

    north_star = NorthStarGoal(
        resolution_id=resolution.id,
        goal_statement=north_star_data.get(
            "north_star_statement", "Become your best self"
        ),
        target_date=target_date,
        is_ai_generated=True,
    )
    db.add(north_star)
    await db.commit()
    await db.refresh(north_star)

    return NorthStarResponse(
        id=north_star.id,
        resolution_id=north_star.resolution_id,
        goal_statement=north_star.goal_statement,
        target_date=north_star.target_date,
        is_ai_generated=north_star.is_ai_generated,
        is_edited=north_star.is_edited,
        key_transformations=north_star_data.get("key_transformations"),
        identity_shift=north_star_data.get("identity_shift"),
        why_it_matters=north_star_data.get("why_it_matters"),
    )


@router.get("/{resolution_id}/north-star", response_model=NorthStarResponse)
async def get_north_star(
    resolution_id: int,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the North Star goal for a resolution."""
    result = await db.execute(
        select(NorthStarGoal)
        .join(Resolution)
        .where(
            NorthStarGoal.resolution_id == resolution_id,
            Resolution.user_id == user.id,
        )
    )
    north_star = result.scalar_one_or_none()

    if not north_star:
        raise HTTPException(status_code=404, detail="North Star not found")

    return north_star


@router.put("/{resolution_id}/north-star", response_model=NorthStarResponse)
async def update_north_star(
    resolution_id: int,
    data: NorthStarUpdate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update/edit the North Star goal."""
    result = await db.execute(
        select(NorthStarGoal)
        .join(Resolution)
        .where(
            NorthStarGoal.resolution_id == resolution_id,
            Resolution.user_id == user.id,
        )
    )
    north_star = result.scalar_one_or_none()

    if not north_star:
        raise HTTPException(status_code=404, detail="North Star not found")

    if data.goal_statement is not None:
        north_star.goal_statement = data.goal_statement

    north_star.is_edited = True
    await db.commit()
    await db.refresh(north_star)

    return north_star


@router.post("/{resolution_id}/roadmap/refresh", response_model=LivingRoadmapResponse)
async def refresh_living_roadmap(
    resolution_id: int,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Trigger a living roadmap refresh based on recent progress."""
    result = await db.execute(
        select(Resolution)
        .options(
            selectinload(Resolution.milestones),
            selectinload(Resolution.progress_logs),
            selectinload(Resolution.streak),
        )
        .where(Resolution.id == resolution_id, Resolution.user_id == user.id)
    )
    resolution = result.scalar_one_or_none()

    if not resolution:
        raise HTTPException(status_code=404, detail="Resolution not found")

    if not resolution.milestones:
        raise HTTPException(status_code=400, detail="No roadmap to refresh")

    milestones_data = [
        {
            "order": m.order,
            "title": m.title,
            "description": m.description,
            "status": m.status,
        }
        for m in resolution.milestones
    ]

    progress_data = [
        {"content": log.content, "date": str(log.date)}
        for log in (resolution.progress_logs or [])[:20]
    ]

    streak_data = {
        "current_streak": resolution.streak.current_streak if resolution.streak else 0,
        "longest_streak": resolution.streak.longest_streak if resolution.streak else 0,
    }

    update_data = await generate_living_roadmap_update(
        resolution_id=resolution.id,
        goal_statement=resolution.goal_statement,
        category=resolution.category,
        cadence=resolution.cadence,
        current_milestones=milestones_data,
        progress_logs=progress_data,
        streak_data=streak_data,
    )

    likelihood_score = calculate_goal_likelihood_score(
        streak_data=streak_data,
        milestones=milestones_data,
        progress_logs=progress_data,
    )

    next_refresh = calculate_next_refresh_date(resolution.cadence)

    resolution.goal_likelihood_score = likelihood_score
    resolution.next_roadmap_refresh = next_refresh
    resolution.roadmap_needs_refresh = False

    await db.commit()

    sorted_milestones = sorted(resolution.milestones, key=lambda m: m.order)

    return LivingRoadmapResponse(
        resolution_id=resolution.id,
        milestones=[MilestoneResponse.model_validate(m) for m in sorted_milestones],
        needs_refresh=False,
        likelihood_score=likelihood_score,
        next_refresh=next_refresh,
        overall_assessment=update_data.get("overall_assessment"),
    )


@router.get("/{resolution_id}/roadmap/living", response_model=LivingRoadmapResponse)
async def get_living_roadmap(
    resolution_id: int,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get roadmap with living roadmap metadata (likelihood, next refresh)."""
    result = await db.execute(
        select(Resolution)
        .options(selectinload(Resolution.milestones))
        .where(Resolution.id == resolution_id, Resolution.user_id == user.id)
    )
    resolution = result.scalar_one_or_none()

    if not resolution:
        raise HTTPException(status_code=404, detail="Resolution not found")

    if not resolution.milestones:
        raise HTTPException(status_code=404, detail="Roadmap not generated yet")

    sorted_milestones = sorted(resolution.milestones, key=lambda m: m.order)

    return LivingRoadmapResponse(
        resolution_id=resolution.id,
        milestones=[MilestoneResponse.model_validate(m) for m in sorted_milestones],
        needs_refresh=resolution.roadmap_needs_refresh,
        likelihood_score=resolution.goal_likelihood_score,
        next_refresh=resolution.next_roadmap_refresh,
    )


@router.put("/{resolution_id}/roadmap-mode")
async def set_roadmap_mode(
    resolution_id: int,
    data: RoadmapModeUpdate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Set the roadmap mode (ai_generated, manual, streak_only)."""
    result = await db.execute(
        select(Resolution).where(
            Resolution.id == resolution_id, Resolution.user_id == user.id
        )
    )
    resolution = result.scalar_one_or_none()

    if not resolution:
        raise HTTPException(status_code=404, detail="Resolution not found")

    resolution.roadmap_mode = data.mode.value
    await db.commit()

    return {"status": "updated", "mode": resolution.roadmap_mode}


@router.put("/{resolution_id}/manual-roadmap", response_model=RoadmapResponse)
async def save_manual_roadmap(
    resolution_id: int,
    data: ManualRoadmapCreate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Save a manually created roadmap."""
    result = await db.execute(
        select(Resolution)
        .options(selectinload(Resolution.milestones))
        .where(Resolution.id == resolution_id, Resolution.user_id == user.id)
    )
    resolution = result.scalar_one_or_none()

    if not resolution:
        raise HTTPException(status_code=404, detail="Resolution not found")

    if resolution.milestones:
        for milestone in resolution.milestones:
            await db.delete(milestone)

    milestones = []
    for i, m_data in enumerate(data.milestones, start=1):
        milestone = Milestone(
            resolution_id=resolution.id,
            order=i,
            title=m_data.title,
            description=m_data.description,
            verification_criteria=m_data.verification_criteria,
            target_date=m_data.target_date,
        )
        db.add(milestone)
        milestones.append(milestone)

    resolution.roadmap_generated = True
    resolution.roadmap_mode = "manual"

    await db.commit()

    for m in milestones:
        await db.refresh(m)

    return RoadmapResponse(
        resolution_id=resolution.id,
        milestones=[MilestoneResponse.model_validate(m) for m in milestones],
        needs_refresh=False,
    )


@router.post("/ai-feedback", response_model=AIFeedbackResponse)
async def submit_ai_feedback(
    data: AIFeedbackCreate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Submit feedback (thumbs up/down) on AI-generated content."""
    feedback = AIFeedback(
        user_id=user.id,
        content_type=data.content_type,
        content_id=data.content_id,
        rating=data.rating,
        feedback_text=data.feedback_text,
    )
    db.add(feedback)
    await db.commit()
    await db.refresh(feedback)

    # Log to Opik for long-term tracking
    # We need to find the resolution_id for the content
    resolution_id = None
    if feedback.content_type == "roadmap":
        m_result = await db.execute(
            select(Milestone).where(Milestone.id == feedback.content_id)
        )
        milestone = m_result.scalar_one_or_none()
        if milestone:
            resolution_id = milestone.resolution_id
    elif feedback.content_type == "weekly_goal":
        w_result = await db.execute(
            select(WeeklyGoal).where(WeeklyGoal.id == feedback.content_id)
        )
        goal = w_result.scalar_one_or_none()
        if goal:
            resolution_id = goal.resolution_id
    elif feedback.content_type == "north_star":
        n_result = await db.execute(
            select(NorthStarGoal).where(NorthStarGoal.id == feedback.content_id)
        )
        ns = n_result.scalar_one_or_none()
        if ns:
            resolution_id = ns.resolution_id

    if resolution_id:
        await log_roadmap_feedback(
            resolution_id=resolution_id,
            content_type=feedback.content_type,
            content_id=feedback.content_id,
            rating=feedback.rating,
            feedback_text=feedback.feedback_text,
        )

    if feedback.rating == 1:
        # For positive feedback, we might want to do something specific,
        # but for now, just return the feedback.
        pass

    return feedback


@router.post("/ai-feedback/{feedback_id}/regenerate")
async def regenerate_from_feedback(
    feedback_id: int,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Regenerate content using gemini-2.5-pro after negative feedback."""
    result = await db.execute(
        select(AIFeedback).where(
            AIFeedback.id == feedback_id, AIFeedback.user_id == user.id
        )
    )
    feedback = result.scalar_one_or_none()

    if not feedback:
        raise HTTPException(status_code=404, detail="Feedback not found")

    if feedback.rating != "thumbs_down":
        raise HTTPException(
            status_code=400, detail="Can only regenerate from negative feedback"
        )

    if feedback.content_type == "weekly_goal":
        # Get the weekly goal
        goal_result = await db.execute(
            select(WeeklyGoal)
            .join(Resolution)
            .where(WeeklyGoal.id == feedback.content_id, Resolution.user_id == user.id)
        )
        weekly_goal = goal_result.scalar_one_or_none()

        if not weekly_goal:
            raise HTTPException(status_code=404, detail="Weekly goal not found")

        # Get resolution
        res_result = await db.execute(
            select(Resolution).where(Resolution.id == weekly_goal.resolution_id)
        )
        resolution = res_result.scalar_one()

        # Regenerate with pro model
        new_data = await regenerate_weekly_goal_with_feedback(
            resolution_goal=resolution.goal_statement,
            category=resolution.category,
            cadence=resolution.cadence,
            original_goal=weekly_goal.goal_text,
            feedback_text=feedback.feedback_text or "Not specified",
            skill_level=resolution.skill_level,
        )

        # Update the goal
        weekly_goal.goal_text = new_data.get("goal_text", weekly_goal.goal_text)
        feedback.was_regenerated = True
        await db.commit()
        await db.refresh(weekly_goal)

        return {
            "status": "regenerated",
            "content_type": "weekly_goal",
            "new_content": weekly_goal,
        }

    elif feedback.content_type == "north_star":
        # Get the north star
        ns_result = await db.execute(
            select(NorthStarGoal)
            .join(Resolution)
            .where(
                NorthStarGoal.id == feedback.content_id, Resolution.user_id == user.id
            )
        )
        north_star = ns_result.scalar_one_or_none()

        if not north_star:
            raise HTTPException(status_code=404, detail="North Star not found")

        # Get resolution
        res_result = await db.execute(
            select(Resolution).where(Resolution.id == north_star.resolution_id)
        )
        resolution = res_result.scalar_one()

        # Regenerate with pro model
        new_data = await regenerate_north_star_with_feedback(
            resolution_goal=resolution.goal_statement,
            category=resolution.category,
            original_north_star=north_star.goal_statement,
            feedback_text=feedback.feedback_text or "Not specified",
            skill_level=resolution.skill_level,
        )

        # Update the north star
        north_star.goal_statement = new_data.get(
            "north_star_statement", north_star.goal_statement
        )
        north_star.is_ai_generated = True
        feedback.was_regenerated = True
        await db.commit()
        await db.refresh(north_star)

        return {
            "status": "regenerated",
            "content_type": "north_star",
            "new_content": north_star,
        }

    elif feedback.content_type == "roadmap":
        # feedback.content_id is the milestone_id
        m_result = await db.execute(
            select(Milestone)
            .join(Resolution)
            .where(Milestone.id == feedback.content_id, Resolution.user_id == user.id)
        )
        milestone = m_result.scalar_one_or_none()

        if not milestone:
            raise HTTPException(status_code=404, detail="Milestone not found")

        # Get resolution and all milestones
        res_result = await db.execute(
            select(Resolution)
            .options(selectinload(Resolution.milestones))
            .where(Resolution.id == milestone.resolution_id)
        )
        resolution = res_result.scalar_one()

        # Regenerate roadmap with feedback
        original_roadmap = {
            "milestones": [
                {"title": m.title, "description": m.description}
                for m in sorted(resolution.milestones, key=lambda x: x.order)
            ]
        }

        new_roadmap_data = await regenerate_roadmap_with_feedback(
            goal_statement=resolution.goal_statement,
            category=resolution.category,
            skill_level=resolution.skill_level,
            cadence=resolution.cadence,
            original_roadmap=original_roadmap,
            feedback_text=feedback.feedback_text
            or f"Focus on improving specifically: {milestone.title}",
        )

        # Delete old milestones and add new ones
        for m in resolution.milestones:
            await db.delete(m)
        await db.flush()

        today = datetime.utcnow().date()
        new_milestones = []
        for i, m_data in enumerate(new_roadmap_data.get("milestones", []), start=1):
            weeks_offset = sum(
                rm.get("estimated_weeks", 2)
                for rm in new_roadmap_data.get("milestones", [])[: i - 1]
            )
            target_date = today + timedelta(
                weeks=weeks_offset + m_data.get("estimated_weeks", 2)
            )

            new_m = Milestone(
                resolution_id=resolution.id,
                order=i,
                title=m_data.get("title", "Milestone"),
                description=m_data.get("description", ""),
                verification_criteria=m_data.get(
                    "verification_criteria", "Demonstrate understanding"
                ),
                target_date=target_date,
            )
            db.add(new_m)
            new_milestones.append(new_m)

        feedback.was_regenerated = True
        await db.commit()

        for m in new_milestones:
            await db.refresh(m)

        return {
            "status": "regenerated",
            "content_type": "roadmap",
            "new_content": {
                "resolution_id": resolution.id,
                "milestones": [
                    MilestoneResponse.model_validate(m) for m in new_milestones
                ],
                "needs_refresh": False,
            },
        }

    else:
        raise HTTPException(
            status_code=400,
            detail=f"Regeneration not supported for content type: {feedback.content_type}",
        )


@router.get("/weekly-goal/aggregated", response_model=AggregatedWeeklyFocusResponse)
async def get_user_aggregated_focus(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve or generate the combined weekly focus for all user resolutions."""
    today = datetime.utcnow().date()
    # Find current week boundaries (Monday as start)
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)

    # Check for existing focus
    result = await db.execute(
        select(UserWeeklyFocus).where(
            UserWeeklyFocus.user_id == user.id,
            UserWeeklyFocus.week_start == week_start,
        )
    )
    existing_focus = result.scalar_one_or_none()
    if existing_focus:
        return existing_focus

    # Generate new one if not found
    # Get all active resolutions for user
    res_result = await db.execute(
        select(Resolution).where(
            Resolution.user_id == user.id, Resolution.status == "active"
        )
    )
    resolutions = res_result.scalars().all()

    if not resolutions:
        return {
            "id": 0,
            "focus_text": "No active resolutions found. Create one to get started!",
            "micro_actions": [],
            "motivation_note": None,
            "week_start": week_start,
            "week_end": week_end,
            "is_dismissed": False,
        }

    res_dicts = [
        {
            "id": r.id,
            "goal_statement": r.goal_statement,
            "category": r.category,
            "cadence": r.cadence,
            "skill_level": r.skill_level,
        }
        for r in resolutions
    ]

    focus_data = await get_aggregated_weekly_focus(res_dicts)

    new_focus = UserWeeklyFocus(
        user_id=user.id,
        focus_text=focus_data.get("focus_text", ""),
        micro_actions=focus_data.get("micro_actions", []),
        motivation_note=focus_data.get("motivation_note"),
        week_start=week_start,
        week_end=week_end,
    )

    db.add(new_focus)
    await db.commit()
    await db.refresh(new_focus)

    return new_focus


@router.put("/weekly-focused/{focus_id}/dismiss")
async def dismiss_aggregated_focus(
    focus_id: int,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark the aggregated focus as dismissed."""
    if focus_id == 0:
        return {"status": "success"}

    result = await db.execute(
        select(UserWeeklyFocus).where(
            UserWeeklyFocus.id == focus_id, UserWeeklyFocus.user_id == user.id
        )
    )
    focus = result.scalar_one_or_none()
    if not focus:
        raise HTTPException(status_code=404, detail="Focus not found")

    focus.is_dismissed = True
    await db.commit()
    return {"status": "success"}
