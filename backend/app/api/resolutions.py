from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import get_db, Resolution, Milestone, Streak
from app.core import get_current_user
from app.schemas import (
    ResolutionCreate,
    ResolutionResponse,
    RoadmapResponse,
    MilestoneResponse,
    NegotiationRequest,
    NegotiationResponse,
    ExistingResolutionContext,
    MilestoneUpdate,
)
from app.agents import generate_roadmap, analyze_feasibility


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
        learning_sources=[],  # Removed learning sources
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
