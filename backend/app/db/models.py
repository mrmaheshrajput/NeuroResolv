from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, Integer, Float, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class User(Base):
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    resolutions: Mapped[list["Resolution"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Resolution(Base):
    __tablename__ = "resolutions"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[str] = mapped_column(Text)
    goal_statement: Mapped[str] = mapped_column(Text)
    daily_time_minutes: Mapped[int] = mapped_column(Integer, default=30)
    duration_days: Mapped[int] = mapped_column(Integer, default=30)
    status: Mapped[str] = mapped_column(String(50), default="active")
    current_day: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user: Mapped["User"] = relationship(back_populates="resolutions")
    syllabus: Mapped[Optional["Syllabus"]] = relationship(back_populates="resolution", uselist=False, cascade="all, delete-orphan")
    daily_sessions: Mapped[list["DailySession"]] = relationship(back_populates="resolution", cascade="all, delete-orphan")
    learning_metrics: Mapped[list["LearningMetric"]] = relationship(back_populates="resolution", cascade="all, delete-orphan")


class Syllabus(Base):
    __tablename__ = "syllabi"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    resolution_id: Mapped[int] = mapped_column(ForeignKey("resolutions.id"), unique=True, index=True)
    content: Mapped[dict] = mapped_column(JSON)
    total_days: Mapped[int] = mapped_column(Integer)
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_adapted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    resolution: Mapped["Resolution"] = relationship(back_populates="syllabus")


class DailySession(Base):
    __tablename__ = "daily_sessions"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    resolution_id: Mapped[int] = mapped_column(ForeignKey("resolutions.id"), index=True)
    day_number: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(500))
    content: Mapped[str] = mapped_column(Text)
    summary: Mapped[str] = mapped_column(Text)
    concepts: Mapped[list] = mapped_column(JSON, default=list)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    is_reinforcement: Mapped[bool] = mapped_column(Boolean, default=False)
    reinforced_concepts: Mapped[list] = mapped_column(JSON, default=list)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    resolution: Mapped["Resolution"] = relationship(back_populates="daily_sessions")
    quiz: Mapped[Optional["Quiz"]] = relationship(back_populates="session", uselist=False, cascade="all, delete-orphan")


class Quiz(Base):
    __tablename__ = "quizzes"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("daily_sessions.id"), unique=True, index=True)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    passed: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    session: Mapped["DailySession"] = relationship(back_populates="quiz")
    questions: Mapped[list["QuizQuestion"]] = relationship(back_populates="quiz", cascade="all, delete-orphan")
    responses: Mapped[list["QuizResponse"]] = relationship(back_populates="quiz", cascade="all, delete-orphan")


class QuizQuestion(Base):
    __tablename__ = "quiz_questions"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    quiz_id: Mapped[int] = mapped_column(ForeignKey("quizzes.id"), index=True)
    question_type: Mapped[str] = mapped_column(String(50))
    question_text: Mapped[str] = mapped_column(Text)
    options: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    correct_answer: Mapped[str] = mapped_column(Text)
    concept: Mapped[str] = mapped_column(String(255))
    difficulty: Mapped[str] = mapped_column(String(50), default="medium")
    order: Mapped[int] = mapped_column(Integer)
    
    quiz: Mapped["Quiz"] = relationship(back_populates="questions")


class QuizResponse(Base):
    __tablename__ = "quiz_responses"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    quiz_id: Mapped[int] = mapped_column(ForeignKey("quizzes.id"), index=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("quiz_questions.id"), index=True)
    user_answer: Mapped[str] = mapped_column(Text)
    is_correct: Mapped[bool] = mapped_column(Boolean)
    feedback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    quiz: Mapped["Quiz"] = relationship(back_populates="responses")


class LearningMetric(Base):
    __tablename__ = "learning_metrics"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    resolution_id: Mapped[int] = mapped_column(ForeignKey("resolutions.id"), index=True)
    concept: Mapped[str] = mapped_column(String(255))
    mastery_score: Mapped[float] = mapped_column(Float, default=0.0)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    correct_count: Mapped[int] = mapped_column(Integer, default=0)
    last_tested_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    needs_reinforcement: Mapped[bool] = mapped_column(Boolean, default=False)
    
    resolution: Mapped["Resolution"] = relationship(back_populates="learning_metrics")
