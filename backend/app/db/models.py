from datetime import datetime
from typing import Optional

from app.db.database import Base
from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    resolutions: Mapped[list["Resolution"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Resolution(Base):
    __tablename__ = "resolutions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)

    goal_statement: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(100), default="learning")
    skill_level: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    cadence: Mapped[str] = mapped_column(String(50), default="daily")

    status: Mapped[str] = mapped_column(String(50), default="active")
    current_milestone: Mapped[int] = mapped_column(Integer, default=0)
    roadmap_generated: Mapped[bool] = mapped_column(Boolean, default=False)
    roadmap_needs_refresh: Mapped[bool] = mapped_column(Boolean, default=False)

    roadmap_mode: Mapped[str] = mapped_column(
        String(50), default="ai_generated"
    )  # ai_generated, manual, streak_only
    goal_likelihood_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    next_roadmap_refresh: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    user: Mapped["User"] = relationship(back_populates="resolutions")
    milestones: Mapped[list["Milestone"]] = relationship(
        back_populates="resolution", cascade="all, delete-orphan"
    )
    progress_logs: Mapped[list["ProgressLog"]] = relationship(
        back_populates="resolution", cascade="all, delete-orphan"
    )
    streak: Mapped[Optional["Streak"]] = relationship(
        back_populates="resolution", uselist=False, cascade="all, delete-orphan"
    )
    weekly_goals: Mapped[list["WeeklyGoal"]] = relationship(
        back_populates="resolution", cascade="all, delete-orphan"
    )
    north_star: Mapped[Optional["NorthStarGoal"]] = relationship(
        back_populates="resolution", uselist=False, cascade="all, delete-orphan"
    )


class Milestone(Base):
    __tablename__ = "milestones"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    resolution_id: Mapped[int] = mapped_column(ForeignKey("resolutions.id"), index=True)

    order: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[str] = mapped_column(Text)
    verification_criteria: Mapped[str] = mapped_column(Text)
    target_date: Mapped[Optional[datetime]] = mapped_column(Date, nullable=True)

    status: Mapped[str] = mapped_column(String(50), default="pending")
    is_edited: Mapped[bool] = mapped_column(Boolean, default=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    resolution: Mapped["Resolution"] = relationship(back_populates="milestones")


class ProgressLog(Base):
    __tablename__ = "progress_logs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    resolution_id: Mapped[int] = mapped_column(ForeignKey("resolutions.id"), index=True)

    date: Mapped[datetime] = mapped_column(Date, default=datetime.utcnow)
    content: Mapped[str] = mapped_column(Text)
    input_type: Mapped[str] = mapped_column(String(50), default="text")

    source_reference: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    duration_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    concepts_claimed: Mapped[list] = mapped_column(JSON, default=list)

    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    verification_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    resolution: Mapped["Resolution"] = relationship(back_populates="progress_logs")
    verification_quiz: Mapped[Optional["VerificationQuiz"]] = relationship(
        back_populates="progress_log", uselist=False, cascade="all, delete-orphan"
    )


class VerificationQuiz(Base):
    __tablename__ = "verification_quizzes"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    progress_log_id: Mapped[int] = mapped_column(
        ForeignKey("progress_logs.id"), unique=True, index=True
    )

    questions: Mapped[list] = mapped_column(JSON, default=list)
    responses: Mapped[list] = mapped_column(JSON, default=list)

    quiz_type: Mapped[str] = mapped_column(String(50), default="contextual")
    score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    passed: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)

    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    progress_log: Mapped["ProgressLog"] = relationship(
        back_populates="verification_quiz"
    )


class Streak(Base):
    __tablename__ = "streaks"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    resolution_id: Mapped[int] = mapped_column(
        ForeignKey("resolutions.id"), unique=True, index=True
    )

    current_streak: Mapped[int] = mapped_column(Integer, default=0)
    longest_streak: Mapped[int] = mapped_column(Integer, default=0)
    total_verified_days: Mapped[int] = mapped_column(Integer, default=0)

    last_log_date: Mapped[Optional[datetime]] = mapped_column(Date, nullable=True)
    last_verified_date: Mapped[Optional[datetime]] = mapped_column(Date, nullable=True)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    resolution: Mapped["Resolution"] = relationship(back_populates="streak")


class WeeklyReflection(Base):
    __tablename__ = "weekly_reflections"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    resolution_id: Mapped[int] = mapped_column(ForeignKey("resolutions.id"), index=True)

    week_number: Mapped[int] = mapped_column(Integer)
    week_start: Mapped[datetime] = mapped_column(Date)

    prompt: Mapped[str] = mapped_column(Text)
    response: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class WeeklyGoal(Base):
    """AI-generated weekly suggestion for near-term focus"""

    __tablename__ = "weekly_goals"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    resolution_id: Mapped[int] = mapped_column(ForeignKey("resolutions.id"), index=True)

    goal_text: Mapped[str] = mapped_column(Text)
    week_start: Mapped[datetime] = mapped_column(Date)
    week_end: Mapped[datetime] = mapped_column(Date)

    is_dismissed: Mapped[bool] = mapped_column(Boolean, default=False)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    resolution: Mapped["Resolution"] = relationship(back_populates="weekly_goals")


class NorthStarGoal(Base):
    """End-of-year vision representing user's transformation journey"""

    __tablename__ = "north_star_goals"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    resolution_id: Mapped[int] = mapped_column(
        ForeignKey("resolutions.id"), unique=True, index=True
    )

    goal_statement: Mapped[str] = mapped_column(Text)
    target_date: Mapped[datetime] = mapped_column(Date)

    is_ai_generated: Mapped[bool] = mapped_column(Boolean, default=True)
    is_edited: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    resolution: Mapped["Resolution"] = relationship(back_populates="north_star")


class AIFeedback(Base):
    """User feedback on AI-generated content for improvement"""

    __tablename__ = "ai_feedback"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)

    content_type: Mapped[str] = mapped_column(
        String(50)
    )  # roadmap, weekly_goal, north_star
    content_id: Mapped[int] = mapped_column(Integer)

    rating: Mapped[str] = mapped_column(String(20))  # thumbs_up, thumbs_down
    feedback_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    was_regenerated: Mapped[bool] = mapped_column(Boolean, default=False)
    regenerated_content_id: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship()


class UserWeeklyFocus(Base):
    """AI-generated combined weekly focus for users with multiple resolutions"""

    __tablename__ = "user_weekly_focus"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)

    focus_text: Mapped[str] = mapped_column(Text)
    micro_actions: Mapped[list] = mapped_column(JSON, default=list)
    motivation_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    week_start: Mapped[datetime] = mapped_column(Date)
    week_end: Mapped[datetime] = mapped_column(Date)

    is_dismissed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship()
