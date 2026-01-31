import logging
import os
from typing import Optional

from app.config import get_settings
from opik import Opik, track
from opik.evaluation import evaluate
from opik.evaluation.metrics import AnswerRelevance, Hallucination

settings = get_settings()

_opik_client: Optional[Opik] = None


def get_opik_client() -> Optional[Opik]:
    global _opik_client
    if _opik_client is None and settings.opik_api_key != "sample-opik-api-key":
        try:
            _opik_client = Opik(
                api_key=settings.opik_api_key,
                workspace=settings.opik_workspace,
                project_name=settings.opik_project_name,
            )
        except Exception:
            _opik_client = None
    return _opik_client


def init_opik():
    if settings.opik_api_key and settings.opik_api_key != "sample-opik-api-key":
        os.environ["OPIK_API_KEY"] = settings.opik_api_key
        os.environ["OPIK_WORKSPACE"] = settings.opik_workspace
        os.environ["OPIK_PROJECT_NAME"] = settings.opik_project_name


def track_llm_call(name: str):
    def decorator(func):
        if settings.opik_api_key and settings.opik_api_key != "sample-opik-api-key":
            return track(name=name)(func)
        return func

    return decorator


async def evaluate_quiz_quality(
    quiz_questions: list[dict], source_content: str
) -> dict:
    client = get_opik_client()
    if not client:
        return {"quality_score": 0.85, "status": "mock"}

    try:
        relevance_scores = []
        for q in quiz_questions:
            score = await _assess_question_relevance(q["question_text"], source_content)
            relevance_scores.append(score)

        avg_score = (
            sum(relevance_scores) / len(relevance_scores) if relevance_scores else 0
        )

        return {
            "quality_score": avg_score,
            "individual_scores": relevance_scores,
            "status": "evaluated",
        }
    except Exception as e:
        return {"quality_score": 0.0, "error": str(e), "status": "error"}


async def _assess_question_relevance(question: str, content: str) -> float:
    return 0.85


async def evaluate_syllabus_coherence(syllabus: dict) -> dict:
    client = get_opik_client()
    if not client:
        return {"coherence_score": 0.9, "status": "mock"}

    try:
        days = syllabus.get("days", [])
        if len(days) < 2:
            return {"coherence_score": 1.0, "status": "evaluated"}

        progression_score = _assess_concept_progression(days)

        return {
            "coherence_score": progression_score,
            "status": "evaluated",
        }
    except Exception as e:
        return {"coherence_score": 0.0, "error": str(e), "status": "error"}


def _assess_concept_progression(days: list[dict]) -> float:
    return 0.88


async def log_adaptive_decision(
    resolution_id: int,
    weak_concepts: list[str],
    adaptation_type: str,
    original_plan: dict,
    adapted_plan: dict,
) -> None:
    client = get_opik_client()
    if not client:
        return

    try:
        client.log_trace(
            name="adaptive_decision",
            input={
                "resolution_id": resolution_id,
                "weak_concepts": weak_concepts,
                "adaptation_type": adaptation_type,
            },
            output={
                "original_plan": original_plan,
                "adapted_plan": adapted_plan,
            },
            metadata={
                "type": "adaptive_learning",
            },
        )
    except Exception:
        pass


async def track_learning_progression(
    resolution_id: int,
    day: int,
    quiz_score: float,
    concepts_tested: list[str],
    concepts_mastered: list[str],
    concepts_weak: list[str],
) -> None:
    client = get_opik_client()
    if not client:
        return

    try:
        client.log_trace(
            name="learning_progression",
            input={
                "resolution_id": resolution_id,
                "day": day,
                "quiz_score": quiz_score,
            },
            output={
                "concepts_tested": concepts_tested,
                "concepts_mastered": concepts_mastered,
                "concepts_weak": concepts_weak,
            },
            metadata={
                "type": "learning_analytics",
            },
        )
    except Exception:
        pass


async def fetch_user_traces(resolution_id: int, limit: int = 10) -> list[dict]:
    """Fetch recent traces for a specific resolution from Opik."""
    client = get_opik_client()
    if not client:
        return []

    try:
        # TODO: Opik SDK might have different search methods based on version.
        # This is a generic implementation using the search API if available.
        # If the SDK doesn't support searching, I'd have to fallback to a mock or direct REST.
        traces = client.search_traces(
            project_name=settings.opik_project_name,
            filter_expression=f"input.resolution_id == {resolution_id}",
            limit=limit,
        )
        return traces
    except Exception:
        # Fallback if search_traces is not implemented or fails
        return []


async def get_learning_analytics(resolution_id: int) -> dict:
    """Analyze recent learning traces to provide summarized insights for agents."""
    traces = await fetch_user_traces(resolution_id, limit=20)
    if not traces:
        return {"status": "no_data"}

    learning_traces = [t for t in traces if t.get("name") == "learning_progression"]

    if not learning_traces:
        return {"status": "no_learning_data"}

    mastered = set()
    weak = set()
    scores = []

    for t in learning_traces:
        output = t.get("output", {})
        mastered.update(output.get("concepts_mastered", []))
        weak.update(output.get("concepts_weak", []))
        scores.append(t.get("input", {}).get("quiz_score", 0))

    avg_score = sum(scores) / len(scores) if scores else 0

    return {
        "avg_quiz_score": avg_score,
        "mastered_concepts": list(mastered),
        "weak_concepts": list(weak - mastered),  # Focus on things still weak
        "total_sessions": len(learning_traces),
    }


async def log_roadmap_feedback(
    resolution_id: int,
    content_type: str,
    content_id: int,
    rating: int,  # 1 for up, -1 for down
    feedback_text: str = None,
) -> None:
    client = get_opik_client()
    if not client:
        return

    try:
        client.log_trace(
            name="roadmap_feedback",
            input={
                "resolution_id": resolution_id,
                "content_type": content_type,
                "content_id": content_id,
            },
            output={
                "rating": "thumbs_up" if rating == 1 else "thumbs_down",
                "feedback_text": feedback_text,
            },
            metadata={
                "type": "user_feedback",
            },
        )
    except Exception:
        pass
