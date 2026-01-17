from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class UserBase(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=100)


class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=72)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(UserBase):
    id: int
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class ResolutionBase(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    description: str
    goal_statement: str
    daily_time_minutes: int = Field(default=30, ge=10, le=120)
    duration_days: int = Field(default=30, ge=7, le=90)


class ResolutionCreate(ResolutionBase):
    pass


class ResolutionResponse(ResolutionBase):
    id: int
    user_id: int
    status: str
    current_day: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class SyllabusDay(BaseModel):
    day: int
    title: str
    description: str
    concepts: list[str]
    estimated_minutes: int


class SyllabusResponse(BaseModel):
    id: int
    resolution_id: int
    total_days: int
    days: list[SyllabusDay]
    generated_at: datetime
    
    class Config:
        from_attributes = True


class DailySessionResponse(BaseModel):
    id: int
    resolution_id: int
    day_number: int
    title: str
    content: str
    summary: str
    concepts: list[str]
    is_completed: bool
    is_reinforcement: bool
    reinforced_concepts: list[str]
    completed_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class QuizQuestionResponse(BaseModel):
    id: int
    question_type: str
    question_text: str
    options: Optional[list[str]]
    concept: str
    difficulty: str
    order: int
    
    class Config:
        from_attributes = True


class QuizResponse(BaseModel):
    id: int
    session_id: int
    is_completed: bool
    score: Optional[float]
    passed: Optional[bool]
    questions: list[QuizQuestionResponse]
    
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
    weak_concepts: list[str]


class ProgressOverview(BaseModel):
    resolution_id: int
    title: str
    current_day: int
    total_days: int
    completion_percentage: float
    current_streak: int
    longest_streak: int
    average_quiz_score: float
    sessions_completed: int
    quizzes_passed: int
    quizzes_failed: int


class ConceptMastery(BaseModel):
    concept: str
    mastery_score: float
    attempts: int
    needs_reinforcement: bool


class WeakAreasResponse(BaseModel):
    resolution_id: int
    weak_concepts: list[ConceptMastery]
