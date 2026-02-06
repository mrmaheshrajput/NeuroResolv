from datetime import datetime
from typing import List, Optional

from app.core import get_current_user
from app.db import (
    Resolution,
    Streak,
    StreakGroup,
    StreakGroupMember,
    User,
    get_db,
)
from app.schemas import (
    StreakGroupCreate,
    StreakGroupResponse,
    UserEmailValidate,
    UserEmailValidateResponse,
)
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

router = APIRouter(prefix="/streak-groups", tags=["streak-groups"])


@router.post("/validate-email", response_model=UserEmailValidateResponse)
async def validate_user_email(
    data: UserEmailValidate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Validate if an email address exists on the platform."""
    result = await db.execute(select(User).where(User.email == data.email))
    exists = result.scalar_one_or_none() is not None
    return UserEmailValidateResponse(exists=exists)


@router.post("", response_model=StreakGroupResponse)
async def create_streak_group(
    data: StreakGroupCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new streak group with up to 3 people."""
    if len(data.member_emails) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one member email must be provided",
        )

    if len(data.member_emails) > 2:  # Max 3 people including creator
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 3 people can be added in a group",
        )

    # Check if resolution exists and belongs to user
    res_result = await db.execute(
        select(Resolution).where(
            Resolution.id == data.resolution_id, Resolution.user_id == user.id
        )
    )
    resolution = res_result.scalar_one_or_none()
    if not resolution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resolution not found",
        )

    # Check if user already in a group for this resolution
    # Join StreakGroup to check is_active status
    existing_member_result = await db.execute(
        select(StreakGroupMember)
        .join(StreakGroup, StreakGroupMember.group_id == StreakGroup.id)
        .where(
            StreakGroupMember.resolution_id == resolution.id,
            StreakGroup.is_active == True,
        )
    )
    if existing_member_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You are already in a streak group for this resolution",
        )

    # Validate all member emails exist and get their users
    member_users = []
    for email in data.member_emails:
        u_result = await db.execute(select(User).where(User.email == email))
        u = u_result.scalar_one_or_none()
        if not u:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with email {email} not found",
            )
        if u.id == user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You cannot add yourself to the group via email",
            )
        member_users.append(u)

    # Create the group
    group = StreakGroup(created_by=user.id)
    db.add(group)
    await db.flush()

    # Add creator as member
    creator_member = StreakGroupMember(
        group_id=group.id,
        user_id=user.id,
        resolution_id=data.resolution_id,
    )
    db.add(creator_member)

    # Add other members
    # Note: In a real app, we might send invitations.
    # For now, we add them directly as per requirement "validate and add".
    # But wait, we need THEIR resolution_id. This is tricky.
    # Requirement says: "available users in the app".
    # Let's assume they must have at least one active resolution.
    for m_user in member_users:
        # Check if they are already in a group for any of their active resolutions??
        # Or just find their first active resolution and use that.
        m_res_result = await db.execute(
            select(Resolution).where(
                Resolution.user_id == m_user.id, Resolution.status == "active"
            )
        )
        m_res = m_res_result.scalar_one_or_none()
        if not m_res:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"User {m_user.email} does not have an active resolution to link",
            )

        # Check if THEY are already in an active group
        m_existing = await db.execute(
            select(StreakGroupMember)
            .join(StreakGroup, StreakGroupMember.group_id == StreakGroup.id)
            .where(
                StreakGroupMember.user_id == m_user.id, StreakGroup.is_active == True
            )
        )
        if m_existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"User {m_user.email} is already in a streak group",
            )

        db.add(
            StreakGroupMember(
                group_id=group.id,
                user_id=m_user.id,
                resolution_id=m_res.id,
            )
        )

    await db.commit()
    await db.refresh(group)

    # Load members with user and streak info for response
    result = await db.execute(
        select(StreakGroup)
        .options(
            selectinload(StreakGroup.members).selectinload(StreakGroupMember.user),
            selectinload(StreakGroup.members)
            .selectinload(StreakGroupMember.resolution)
            .selectinload(Resolution.streak),
        )
        .where(StreakGroup.id == group.id)
    )
    group = result.scalar_one()

    member_infos = []
    for m in group.members:
        member_infos.append(
            {
                "user_id": m.user_id,
                "full_name": m.user.full_name,
                "email": m.user.email,
                "current_streak": (
                    m.resolution.streak.current_streak if m.resolution.streak else 0
                ),
            }
        )

    return {
        "id": group.id,
        "members": member_infos,
        "is_active": group.is_active,
        "created_at": group.created_at,
    }


@router.get("/my-group", response_model=Optional[StreakGroupResponse])
async def get_my_streak_group(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the streak group the current user belongs to."""
    result = await db.execute(
        select(StreakGroup)
        .join(StreakGroupMember)
        .options(
            selectinload(StreakGroup.members).selectinload(StreakGroupMember.user),
            selectinload(StreakGroup.members)
            .selectinload(StreakGroupMember.resolution)
            .selectinload(Resolution.streak),
        )
        .where(StreakGroupMember.user_id == user.id, StreakGroup.is_active == True)
    )
    group = result.scalar_one_or_none()

    if not group:
        return None

    member_infos = []
    for m in group.members:
        member_infos.append(
            {
                "user_id": m.user_id,
                "full_name": m.user.full_name,
                "email": m.user.email,
                "current_streak": (
                    m.resolution.streak.current_streak if m.resolution.streak else 0
                ),
            }
        )

    return {
        "id": group.id,
        "members": member_infos,
        "is_active": group.is_active,
        "created_at": group.created_at,
    }


@router.delete("/{group_id}")
async def leave_streak_group(
    group_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Leave or deactivate a streak group."""
    result = await db.execute(select(StreakGroup).where(StreakGroup.id == group_id))
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    # If creator leaves, deactivate group. If member leaves, just remove them?
    # Requirement: "select upto three people... If any one of them breaks... all looses".
    # Let's keep it simple: any member leaving breaks the group.
    # My brain hurts reading your comments.
    group.is_active = False
    await db.commit()
    return {"message": "Group deactivated"}
