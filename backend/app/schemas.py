from datetime import datetime, date
from typing import Optional
from pydantic import BaseModel, EmailStr, Field
from enum import Enum


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    full_name: str = Field(min_length=1, max_length=100)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class GoalCategory(str, Enum):
    LEARNING = "learning"
    READING = "reading"
    SKILL = "skill"
    FITNESS = "fitness"
    PROFESSIONAL = "professional"
    CREATIVE = "creative"


class SkillLevel(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class Cadence(str, Enum):
    DAILY = "daily"
    THREE_PER_WEEK = "3x_week"
    WEEKDAYS = "weekdays"
    WEEKLY = "weekly"



class NegotiationRequest(BaseModel):
    goal_statement: str
    category: GoalCategory
    skill_level: Optional[SkillLevel] = None
    cadence: Cadence

class NegotiationSuggestion(BaseModel):
    cadence: Cadence
    reason: str

class NegotiationResponse(BaseModel):
    is_feasible: bool
    feedback: str
    suggestion: Optional[NegotiationSuggestion] = None
    streak_trigger: str


class ResolutionCreate(BaseModel):
    goal_statement: str = Field(min_length=10, max_length=1000)
    category: GoalCategory = GoalCategory.LEARNING
    skill_level: Optional[SkillLevel] = None
    cadence: Cadence = Cadence.DAILY


class ResolutionResponse(BaseModel):
    id: int
    user_id: int
    goal_statement: str
    category: str
    skill_level: Optional[str]
    cadence: str
    status: str
    current_milestone: int
    roadmap_generated: bool
    roadmap_needs_refresh: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class MilestoneCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    description: str
    verification_criteria: str
    target_date: Optional[date] = None


class MilestoneUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    verification_criteria: Optional[str] = None
    target_date: Optional[date] = None


class MilestoneResponse(BaseModel):
    id: int
    resolution_id: int
    order: int
    title: str
    description: str
    verification_criteria: str
    target_date: Optional[date]
    status: str
    is_edited: bool
    completed_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class RoadmapResponse(BaseModel):
    resolution_id: int
    milestones: list[MilestoneResponse]
    needs_refresh: bool


class ProgressLogCreate(BaseModel):
    content: str = Field(min_length=1)
    input_type: str = "text"
    source_reference: Optional[str] = None
    duration_minutes: Optional[int] = None


class ProgressLogResponse(BaseModel):
    id: int
    resolution_id: int
    date: date
    content: str
    input_type: str
    source_reference: Optional[str]
    duration_minutes: Optional[int]
    concepts_claimed: list
    verified: bool
    verification_score: Optional[float]
    created_at: datetime
    
    class Config:
        from_attributes = True


class QuizQuestion(BaseModel):
    id: int
    question_type: str
    question_text: str
    options: Optional[list[str]] = None
    concept: Optional[str] = None


class VerificationQuizResponse(BaseModel):
    id: int
    progress_log_id: int
    quiz_type: str
    questions: list[QuizQuestion]
    is_completed: bool
    score: Optional[float]
    passed: Optional[bool]
    
    class Config:
        from_attributes = True


class QuizAnswerSubmit(BaseModel):
    question_id: int
    answer: str


class QuizSubmission(BaseModel):
    answers: list[QuizAnswerSubmit]


class QuizResultResponse(BaseModel):
    quiz_id: int
    score: float
    passed: bool
    total_questions: int
    correct_answers: int
    feedback: dict
    streak_updated: bool


class StreakResponse(BaseModel):
    resolution_id: int
    current_streak: int
    longest_streak: int
    total_verified_days: int
    last_log_date: Optional[date]
    last_verified_date: Optional[date]
    
    class Config:
        from_attributes = True


class ProgressOverview(BaseModel):
    resolution_id: int
    goal_statement: str
    category: str
    current_milestone: int
    total_milestones: int
    milestones_completed: int
    current_streak: int
    longest_streak: int
    total_verified_days: int
    logs_this_week: int


class WeeklyReflectionPrompt(BaseModel):
    id: int
    week_number: int
    prompt: str
    is_completed: bool


class WeeklyReflectionSubmit(BaseModel):
    response: str


class VoiceNoteUpload(BaseModel):
    audio_base64: str
    duration_seconds: Optional[int] = None


class TranscriptionResponse(BaseModel):
    text: str
    duration_seconds: Optional[int]
