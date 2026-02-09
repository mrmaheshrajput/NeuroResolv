from mcp.server.fastmcp import FastMCP, Context
from app.db import (
    async_session_maker,
    Resolution,
    UserWeeklyFocus,
    Milestone,
    ProgressLog,
    User,
)
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from datetime import datetime, date, timedelta
import os
from app.core.context import current_user_id

# Initialize FastMCP server
mcp = FastMCP("NeuroResolv")


async def get_authenticated_user_id() -> int:
    """Retrieve the authenticated user ID from context or raise error."""
    user_id = current_user_id.get()
    if not user_id:
        # For hackathon convenience, we COULD fallback to the first user
        # Fallback to first user only if a special env var is set
        if os.getenv("MCP_ALLOW_UNAUTHENTICATED_DEMO") == "true":
            async with async_session_maker() as session:
                stmt = select(User.id).order_by(User.id).limit(1)
                res = await session.execute(stmt)
                return res.scalar()
        raise Exception(
            "Authentication required: Please provide a valid Bearer token in the Authorization header."
        )
    return user_id


@mcp.tool()
async def list_resolutions_mcp() -> str:
    """List all active resolutions for the authenticated user."""
    user_id = await get_authenticated_user_id()

    async with async_session_maker() as session:
        stmt = select(Resolution).where(
            Resolution.user_id == user_id, Resolution.status == "active"
        )
        result = await session.execute(stmt)
        resolutions = result.scalars().all()

        if not resolutions:
            return "No active resolutions found."

        output = "Active Resolutions:\n"
        for res in resolutions:
            output += f"- ID: {res.id} | Goal: {res.goal_statement} | Category: {res.category}\n"
        return output


@mcp.tool()
async def get_weekly_focus_mcp() -> str:
    """Get your combined weekly focus for all active resolutions."""
    user_id = await get_authenticated_user_id()

    async with async_session_maker() as session:
        today = datetime.utcnow().date()
        week_start = today - timedelta(days=today.weekday())

        stmt = (
            select(UserWeeklyFocus)
            .where(
                UserWeeklyFocus.user_id == user_id,
                UserWeeklyFocus.week_start == week_start,
            )
            .order_by(UserWeeklyFocus.created_at.desc())
        )

        result = await session.execute(stmt)
        focus = result.scalars().first()

        if not focus:
            return "No weekly focus generated for this week yet."

        output = f"Weekly Focus: {focus.focus_text}\n"
        if focus.micro_actions:
            output += "\nMicro Actions:\n"
            for action in focus.micro_actions:
                output += f"- {action}\n"
        return output


@mcp.tool()
async def get_milestones_mcp(resolution_id: int) -> str:
    """Get the roadmap/milestones for a specific resolution."""
    user_id = await get_authenticated_user_id()

    async with async_session_maker() as session:
        stmt = (
            select(Resolution)
            .options(selectinload(Resolution.milestones))
            .where(Resolution.id == resolution_id, Resolution.user_id == user_id)
        )
        result = await session.execute(stmt)
        resolution = result.scalar_one_or_none()

        if not resolution:
            return f"Resolution {resolution_id} not found or access denied."

        if not resolution.milestones:
            return "No milestones found for this resolution."

        output = f"Milestones for '{resolution.goal_statement}':\n"
        for m in sorted(resolution.milestones, key=lambda x: x.order):
            status_icon = "✅" if m.status == "completed" else "⏳"
            output += f"{status_icon} [{m.order}] {m.title}: {m.description}\n"
        return output


@mcp.tool()
async def check_in_mcp(resolution_id: int, content: str) -> str:
    """
    Log a text-only progress update for a resolution.
    Use this to report what you've done today.
    """
    user_id = await get_authenticated_user_id()

    async with async_session_maker() as session:
        # Get resolution and ensure it belongs to user
        stmt = (
            select(Resolution)
            .options(
                selectinload(Resolution.streak), selectinload(Resolution.progress_logs)
            )
            .where(Resolution.id == resolution_id, Resolution.user_id == user_id)
        )
        result = await session.execute(stmt)
        resolution = result.scalar_one_or_none()

        if not resolution:
            return "Resolution not found or access denied."

        # Check if already logged today
        today = date.today()
        stmt = select(ProgressLog).where(
            ProgressLog.resolution_id == resolution_id, ProgressLog.date == today
        )
        existing = await session.execute(stmt)
        if existing.scalar_one_or_none():
            return "Progress already logged for today."

        # Analyze check-in (requires Gemini)
        from app.agents.checkin_agent import analyze_checkin

        # Get recent history
        history_summary = "\n".join(
            [f"- {l.date}: {l.content}" for l in resolution.progress_logs[-10:]]
        )

        # Get current milestone
        stmt = (
            select(Milestone)
            .where(
                Milestone.resolution_id == resolution_id,
                Milestone.status == "in_progress",
            )
            .order_by(Milestone.order)
        )
        m_result = await session.execute(stmt)
        current_milestone = m_result.scalar_one_or_none()

        milestone_context = (
            f"\nCURRENT MILESTONE: {current_milestone.title}"
            if current_milestone
            else ""
        )

        ai_result = await analyze_checkin(
            input_type="text",
            content=content,
            goal_context=f"{resolution.goal_statement}{milestone_context}",
            recent_history=history_summary,
            metadata={"resolution_id": resolution_id, "customer_id": user_id},
        )

        final_content = ai_result.get("description", content)
        reflection = ai_result.get("reflection", "Great work!")

        progress_log = ProgressLog(
            resolution_id=resolution_id,
            date=today,
            content=final_content,
            input_type="text",
            ai_reflection=reflection,
            verified=True,
        )
        session.add(progress_log)

        # Update streak
        if resolution.streak:
            resolution.streak.current_streak += 1
            resolution.streak.last_log_date = today
            if resolution.streak.current_streak > resolution.streak.longest_streak:
                resolution.streak.longest_streak = resolution.streak.current_streak

        await session.commit()
        return f"Progress logged! AI Reflection: {reflection}"
