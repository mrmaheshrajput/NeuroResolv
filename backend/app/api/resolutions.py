from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db import get_db, User, Resolution, Syllabus, DailySession
from app.core import get_current_user
from app.schemas import ResolutionCreate, ResolutionResponse, SyllabusResponse, SyllabusDay
from app.services import process_pdf, process_epub, process_text
from app.agents import generate_syllabus
from app.observability import evaluate_syllabus_coherence

router = APIRouter(prefix="/resolutions", tags=["Resolutions"])


@router.post("", response_model=ResolutionResponse, status_code=status.HTTP_201_CREATED)
async def create_resolution(
    resolution_data: ResolutionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    new_resolution = Resolution(
        user_id=current_user.id,
        title=resolution_data.title,
        description=resolution_data.description,
        goal_statement=resolution_data.goal_statement,
        daily_time_minutes=resolution_data.daily_time_minutes,
        duration_days=resolution_data.duration_days,
    )
    
    db.add(new_resolution)
    await db.commit()
    await db.refresh(new_resolution)
    
    return ResolutionResponse.model_validate(new_resolution)


@router.get("", response_model=list[ResolutionResponse])
async def list_resolutions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Resolution)
        .where(Resolution.user_id == current_user.id)
        .order_by(Resolution.created_at.desc())
    )
    resolutions = result.scalars().all()
    return [ResolutionResponse.model_validate(r) for r in resolutions]


@router.get("/{resolution_id}", response_model=ResolutionResponse)
async def get_resolution(
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
    
    return ResolutionResponse.model_validate(resolution)


@router.post("/{resolution_id}/upload")
async def upload_content(
    resolution_id: int,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
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
    
    content = await file.read()
    filename = file.filename or "unknown"
    
    if filename.lower().endswith(".pdf"):
        process_result = await process_pdf(content, resolution_id)
    elif filename.lower().endswith(".epub"):
        process_result = await process_epub(content, resolution_id)
    elif filename.lower().endswith(".txt") or filename.lower().endswith(".md"):
        text_content = content.decode("utf-8")
        process_result = await process_text(text_content, resolution_id, source=filename)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file type. Please upload PDF, EPUB, TXT, or MD files.",
        )
    
    return {
        "message": "Content uploaded and processed successfully",
        "filename": filename,
        "processing_result": process_result,
    }


@router.post("/{resolution_id}/generate-syllabus", response_model=SyllabusResponse)
async def generate_resolution_syllabus(
    resolution_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Resolution)
        .options(selectinload(Resolution.syllabus))
        .where(Resolution.id == resolution_id, Resolution.user_id == current_user.id)
    )
    resolution = result.scalar_one_or_none()
    
    if not resolution:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resolution not found")
    
    syllabus_content = await generate_syllabus(
        goal_statement=resolution.goal_statement,
        resolution_id=resolution_id,
        duration_days=resolution.duration_days,
        daily_minutes=resolution.daily_time_minutes,
    )
    
    await evaluate_syllabus_coherence(syllabus_content)
    
    if resolution.syllabus:
        resolution.syllabus.content = syllabus_content
        resolution.syllabus.total_days = syllabus_content.get("total_days", resolution.duration_days)
        resolution.syllabus.last_adapted_at = datetime.utcnow()
    else:
        new_syllabus = Syllabus(
            resolution_id=resolution_id,
            content=syllabus_content,
            total_days=syllabus_content.get("total_days", resolution.duration_days),
        )
        db.add(new_syllabus)
    
    await db.commit()
    
    result = await db.execute(
        select(Syllabus).where(Syllabus.resolution_id == resolution_id)
    )
    syllabus = result.scalar_one()
    
    await _create_daily_sessions(db, resolution, syllabus_content)
    
    days = [
        SyllabusDay(
            day=d.get("day", i + 1),
            title=d.get("title", f"Day {i + 1}"),
            description=d.get("description", ""),
            concepts=d.get("concepts", []),
            estimated_minutes=d.get("estimated_minutes", resolution.daily_time_minutes),
        )
        for i, d in enumerate(syllabus_content.get("days", []))
    ]
    
    return SyllabusResponse(
        id=syllabus.id,
        resolution_id=resolution_id,
        total_days=syllabus.total_days,
        days=days,
        generated_at=syllabus.generated_at,
    )


@router.get("/{resolution_id}/syllabus", response_model=SyllabusResponse)
async def get_syllabus(
    resolution_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Syllabus)
        .join(Resolution)
        .where(Syllabus.resolution_id == resolution_id, Resolution.user_id == current_user.id)
    )
    syllabus = result.scalar_one_or_none()
    
    if not syllabus:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Syllabus not found")
    
    result = await db.execute(
        select(Resolution).where(Resolution.id == resolution_id)
    )
    resolution = result.scalar_one()
    
    syllabus_content = syllabus.content or {}
    days = [
        SyllabusDay(
            day=d.get("day", i + 1),
            title=d.get("title", f"Day {i + 1}"),
            description=d.get("description", ""),
            concepts=d.get("concepts", []),
            estimated_minutes=d.get("estimated_minutes", resolution.daily_time_minutes),
        )
        for i, d in enumerate(syllabus_content.get("days", []))
    ]
    
    return SyllabusResponse(
        id=syllabus.id,
        resolution_id=resolution_id,
        total_days=syllabus.total_days,
        days=days,
        generated_at=syllabus.generated_at,
    )


async def _create_daily_sessions(
    db: AsyncSession,
    resolution: Resolution,
    syllabus_content: dict,
) -> None:
    result = await db.execute(
        select(DailySession).where(DailySession.resolution_id == resolution.id)
    )
    existing_sessions = result.scalars().all()
    
    for session in existing_sessions:
        await db.delete(session)
    
    days = syllabus_content.get("days", [])
    for day_data in days:
        session = DailySession(
            resolution_id=resolution.id,
            day_number=day_data.get("day", 1),
            title=day_data.get("title", "Learning Session"),
            content=day_data.get("description", ""),
            summary=day_data.get("description", "")[:500],
            concepts=day_data.get("concepts", []),
        )
        db.add(session)
    
    await db.commit()
