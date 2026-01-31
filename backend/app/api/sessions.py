from datetime import datetime
from typing import Optional

from app.agents import adapt_learning_path, generate_quiz, grade_short_answer
from app.core import get_current_user
from app.db import DailySession, LearningMetric, Quiz, QuizQuestion
from app.db import QuizResponse as QuizResponseModel
from app.db import Resolution, User, get_db
from app.observability import evaluate_quiz_quality, track_learning_progression
from app.schemas import (
    DailySessionResponse,
    QuizQuestionResponse,
    QuizResponse,
    QuizResultResponse,
    QuizSubmission,
)
from app.services import query_collection
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

router = APIRouter(prefix="/sessions", tags=["Learning Sessions"])


@router.get("/today", response_model=Optional[DailySessionResponse])
async def get_today_session(
    resolution_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Resolution).where(
            Resolution.id == resolution_id, Resolution.user_id == current_user.id
        )
    )
    resolution = result.scalar_one_or_none()

    if not resolution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Resolution not found"
        )

    current_day = resolution.current_day + 1

    result = await db.execute(
        select(DailySession).where(
            DailySession.resolution_id == resolution_id,
            DailySession.day_number == current_day,
        )
    )
    session = result.scalar_one_or_none()

    if not session:
        return None

    if not session.content or len(session.content) < 100:
        content_result = await query_collection(
            resolution_id,
            session.title,
            n_results=3,
        )

        if content_result.get("documents") and content_result["documents"][0]:
            session.content = "\n\n".join(content_result["documents"][0])
            await db.commit()

    return DailySessionResponse.model_validate(session)


@router.get("/{session_id}", response_model=DailySessionResponse)
async def get_session(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(DailySession)
        .join(Resolution)
        .where(DailySession.id == session_id, Resolution.user_id == current_user.id)
    )
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
        )

    return DailySessionResponse.model_validate(session)


@router.post("/{session_id}/complete")
async def complete_session(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(DailySession)
        .options(selectinload(DailySession.resolution))
        .join(Resolution)
        .where(DailySession.id == session_id, Resolution.user_id == current_user.id)
    )
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
        )

    session.is_completed = True
    session.completed_at = datetime.utcnow()

    await db.commit()

    return {"message": "Session marked as complete", "session_id": session_id}


@router.get("/{session_id}/quiz", response_model=QuizResponse)
async def get_or_generate_quiz(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(DailySession)
        .options(selectinload(DailySession.quiz).selectinload(Quiz.questions))
        .join(Resolution)
        .where(DailySession.id == session_id, Resolution.user_id == current_user.id)
    )
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
        )

    if session.quiz:
        return _format_quiz_response(session.quiz)

    quiz_data = await generate_quiz(
        session_content=session.content,
        session_title=session.title,
        concepts=session.concepts or [],
    )

    await evaluate_quiz_quality(
        quiz_questions=quiz_data.get("questions", []),
        source_content=session.content,
    )

    new_quiz = Quiz(session_id=session_id)
    db.add(new_quiz)
    await db.commit()
    await db.refresh(new_quiz)

    questions = quiz_data.get("questions", [])
    for i, q in enumerate(questions):
        question = QuizQuestion(
            quiz_id=new_quiz.id,
            question_type=q.get("type", "multiple_choice"),
            question_text=q.get("question", ""),
            options=q.get("options"),
            correct_answer=str(q.get("correct_answer", "")),
            concept=q.get("concept", "general"),
            difficulty=q.get("difficulty", "medium"),
            order=i + 1,
        )
        db.add(question)

    await db.commit()

    result = await db.execute(
        select(Quiz).options(selectinload(Quiz.questions)).where(Quiz.id == new_quiz.id)
    )
    quiz = result.scalar_one()

    return _format_quiz_response(quiz)


@router.post("/{session_id}/quiz/submit", response_model=QuizResultResponse)
async def submit_quiz(
    session_id: int,
    submission: QuizSubmission,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(DailySession)
        .options(
            selectinload(DailySession.quiz).selectinload(Quiz.questions),
            selectinload(DailySession.resolution).selectinload(Resolution.syllabus),
        )
        .join(Resolution)
        .where(DailySession.id == session_id, Resolution.user_id == current_user.id)
    )
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
        )

    if not session.quiz:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Quiz not found"
        )

    quiz = session.quiz
    questions_map = {q.id: q for q in quiz.questions}

    correct_count = 0
    weak_concepts = []
    strong_concepts = []
    feedback = {}

    for answer in submission.answers:
        question = questions_map.get(answer.question_id)
        if not question:
            continue

        if question.question_type == "short_answer":
            grade_result = await grade_short_answer(
                question=question.question_text,
                expected_answer=question.correct_answer,
                user_answer=answer.answer,
                concept=question.concept,
            )
            is_correct = grade_result.get("is_correct", False)
            answer_feedback = grade_result.get("feedback", "")
        else:
            is_correct = (
                answer.answer.strip().lower() == question.correct_answer.strip().lower()
            )
            answer_feedback = (
                "Correct!"
                if is_correct
                else f"The correct answer was: {question.correct_answer}"
            )

        response = QuizResponseModel(
            quiz_id=quiz.id,
            question_id=question.id,
            user_answer=answer.answer,
            is_correct=is_correct,
            feedback=answer_feedback,
        )
        db.add(response)

        if is_correct:
            correct_count += 1
            if question.concept not in strong_concepts:
                strong_concepts.append(question.concept)
        else:
            if question.concept not in weak_concepts:
                weak_concepts.append(question.concept)

        feedback[str(question.id)] = {
            "is_correct": is_correct,
            "feedback": answer_feedback,
            "concept": question.concept,
        }

    total_questions = len(quiz.questions)
    score = (correct_count / total_questions * 100) if total_questions > 0 else 0
    passed = score >= 70

    quiz.is_completed = True
    quiz.score = score
    quiz.passed = passed
    quiz.completed_at = datetime.utcnow()

    resolution = session.resolution
    if passed and session.day_number == resolution.current_day + 1:
        resolution.current_day += 1

    await _update_learning_metrics(db, resolution.id, weak_concepts, strong_concepts)

    await db.commit()

    if not passed and weak_concepts:
        syllabus_content = resolution.syllabus.content if resolution.syllabus else {}
        remaining_days = resolution.duration_days - resolution.current_day

        adaptation = await adapt_learning_path(
            resolution_id=resolution.id,
            quiz_score=score,
            weak_concepts=weak_concepts,
            strong_concepts=strong_concepts,
            current_day=resolution.current_day,
            remaining_days=remaining_days,
            current_syllabus=syllabus_content,
        )

        if adaptation.get("reinforcement_content"):
            await _create_reinforcement_session(
                db, resolution.id, session.day_number, adaptation, weak_concepts
            )

    await track_learning_progression(
        resolution_id=resolution.id,
        day=session.day_number,
        quiz_score=score,
        concepts_tested=list(set(q.concept for q in quiz.questions)),
        concepts_mastered=strong_concepts,
        concepts_weak=weak_concepts,
    )

    return QuizResultResponse(
        quiz_id=quiz.id,
        score=score,
        passed=passed,
        total_questions=total_questions,
        correct_answers=correct_count,
        feedback=feedback,
        weak_concepts=weak_concepts,
    )


@router.get("/history/{resolution_id}", response_model=list[DailySessionResponse])
async def get_session_history(
    resolution_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(DailySession)
        .join(Resolution)
        .where(
            DailySession.resolution_id == resolution_id,
            Resolution.user_id == current_user.id,
        )
        .order_by(DailySession.day_number)
    )
    sessions = result.scalars().all()

    return [DailySessionResponse.model_validate(s) for s in sessions]


def _format_quiz_response(quiz: Quiz) -> QuizResponse:
    questions = [
        QuizQuestionResponse(
            id=q.id,
            question_type=q.question_type,
            question_text=q.question_text,
            options=q.options,
            concept=q.concept,
            difficulty=q.difficulty,
            order=q.order,
        )
        for q in sorted(quiz.questions, key=lambda x: x.order)
    ]

    return QuizResponse(
        id=quiz.id,
        session_id=quiz.session_id,
        is_completed=quiz.is_completed,
        score=quiz.score,
        passed=quiz.passed,
        questions=questions,
    )


async def _update_learning_metrics(
    db: AsyncSession,
    resolution_id: int,
    weak_concepts: list[str],
    strong_concepts: list[str],
) -> None:
    all_concepts = set(weak_concepts + strong_concepts)

    for concept in all_concepts:
        result = await db.execute(
            select(LearningMetric).where(
                LearningMetric.resolution_id == resolution_id,
                LearningMetric.concept == concept,
            )
        )
        metric = result.scalar_one_or_none()

        is_correct = concept in strong_concepts

        if metric:
            metric.attempts += 1
            if is_correct:
                metric.correct_count += 1
            metric.mastery_score = metric.correct_count / metric.attempts
            metric.needs_reinforcement = metric.mastery_score < 0.7
            metric.last_tested_at = datetime.utcnow()
        else:
            new_metric = LearningMetric(
                resolution_id=resolution_id,
                concept=concept,
                mastery_score=1.0 if is_correct else 0.0,
                attempts=1,
                correct_count=1 if is_correct else 0,
                needs_reinforcement=not is_correct,
                last_tested_at=datetime.utcnow(),
            )
            db.add(new_metric)


async def _create_reinforcement_session(
    db: AsyncSession,
    resolution_id: int,
    after_day: int,
    adaptation: dict,
    weak_concepts: list[str],
) -> None:
    reinforcement_content = adaptation.get("reinforcement_content", {})

    reinforcement_session = DailySession(
        resolution_id=resolution_id,
        day_number=after_day,
        title=reinforcement_content.get("title", "Concept Reinforcement"),
        content=reinforcement_content.get("approach", "")
        + "\n\n"
        + "\n".join(reinforcement_content.get("activities", [])),
        summary=f"Reinforcing concepts: {', '.join(weak_concepts)}",
        concepts=weak_concepts,
        is_reinforcement=True,
        reinforced_concepts=weak_concepts,
    )

    db.add(reinforcement_session)
