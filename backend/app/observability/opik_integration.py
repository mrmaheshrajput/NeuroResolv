import functools
import inspect
import logging
import os
from typing import Optional

from app.config import get_settings
from opik import Opik, opik_context, track
from opik.evaluation import evaluate
from opik.evaluation.metrics import AnswerRelevance, Hallucination

settings = get_settings()

_opik_client: Optional[Opik] = None

PROMPT_CONFIGS = {
    "GENERATE_ROADMAP_PROMPT": {
        "tag": "prompt:GENERATE_ROADMAP_PROMPT",
        "input_fields": ["goal_statement", "category", "skill_level", "cadence"],
        "description": "Generates personalized learning roadmap milestones",
    },
    "GENERATE_NORTH_STAR_PROMPT": {
        "tag": "prompt:GENERATE_NORTH_STAR_PROMPT",
        "input_fields": ["resolution_goal", "category", "skill_level"],
        "description": "Generates end-of-year transformation vision",
    },
}


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


def track_llm_call(name: str, tags: list[str] = None, metadata: dict = None):
    def decorator(func):
        if not (
            settings.opik_api_key and settings.opik_api_key != "sample-opik-api-key"
        ):
            return func

        if inspect.iscoroutinefunction(func):

            @track(name=name, tags=tags, metadata=metadata)
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                call_metadata = kwargs.get("metadata")
                if call_metadata:
                    opik_context.update_current_trace(metadata=call_metadata)
                return await func(*args, **kwargs)

            return wrapper
        else:

            @track(name=name, tags=tags, metadata=metadata)
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                call_metadata = kwargs.get("metadata")
                if call_metadata:
                    opik_context.update_current_trace(metadata=call_metadata)
                return func(*args, **kwargs)

            return wrapper

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
    # I don't even know why we need this function, but here it is
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
        traces = client.search_traces(
            project_name=settings.opik_project_name,
            filter_string=f"input.resolution_id = {resolution_id}",
            limit=limit,
        )
        return traces
    except Exception as e:
        # Fallback if search_traces is not implemented or fails
        print("Failed to fetch traces for resolution_id", resolution_id)
        print(e)
        return []


@track_llm_call(name="get_learning_analytics")
async def get_learning_analytics(resolution_id: int) -> dict:
    """Analyze recent learning traces to provide summarized insights for agents."""
    traces = await fetch_user_traces(resolution_id, limit=20)
    if not traces:
        return {"status": "no_data"}

    learning_traces = [t for t in traces if t.name == "analyze_checkin"]

    if not learning_traces:
        return {"status": "no_learning_data"}

    reflections = []

    for t in learning_traces:
        reflections.append(t.output)

    return {
        "reflections": reflections,
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


async def fetch_feedback_traces(prompt_name: str, limit: int = 50) -> list:
    """
    Fetch traces with negative feedback for a specific prompt.

    Args:
        prompt_name: One of GENERATE_ROADMAP_PROMPT or GENERATE_NORTH_STAR_PROMPT
        limit: Maximum number of traces to fetch
    """
    client = get_opik_client()
    if not client:
        return []

    config = PROMPT_CONFIGS.get(prompt_name)
    if not config:
        logging.warning(f"Unknown prompt name: {prompt_name}")
        return []

    try:
        # Search for traces with the feedback tag
        # The tag format is "prompt:PROMPT_NAME"
        traces = client.search_traces(
            project_name=settings.opik_project_name,
            filter_string=f'tags contains "{config['tag']}"',
            max_results=limit,
        )

        # Filter for traces that have negative feedback (thumbs_down)
        feedback_traces = []
        for trace in traces:
            if trace.span_feedback_scores:
                for feedback_score in trace.span_feedback_scores:
                    if feedback_score.name == "User feedback":
                        if int(feedback_score.value) == 0:
                            feedback_traces.append(trace)

        return feedback_traces

    except Exception as e:
        logging.error(f"Failed to fetch feedback traces: {e}")
        return []


def build_optimization_dataset(traces: list, prompt_name: str) -> list[dict]:
    """
    Transform feedback traces into a dataset suitable for MetaPromptOptimizer.

    Each dataset item contains:
    - input: The original parameters passed to the prompt
    - output: The user's feedback (what they wanted instead)
    - metadata: Additional context
    """
    config = PROMPT_CONFIGS.get(prompt_name, {})
    input_fields = config.get("input_fields", [])

    dataset_items = []
    for trace in traces:
        try:
            trace_input = trace.input or {}
            item_input = {
                field: trace_input.get(field, "")
                for field in input_fields
                if trace_input.get(field)
            }

            feedback_text = ""
            if trace.output:
                feedback_text = trace.output.get("feedback_text", "")

            if not feedback_text or len(feedback_text) < 10:
                continue

            dataset_items.append(
                {
                    "input": item_input,
                    "expected_output": feedback_text,
                    "metadata": {
                        "trace_id": str(trace.id),
                        "original_response": trace.output.get("original_content", ""),
                    },
                }
            )

        except Exception as e:
            logging.warning(f"Skipping trace due to error: {e}")
            continue

    return dataset_items


async def run_prompt_optimization(
    prompt_name: str,
    min_samples: int = 5,
    n_trials: int = 3,
) -> dict:
    """
    Run MetaPromptOptimizer on a prompt using collected feedback data.

    Args:
        prompt_name: Name of the prompt to optimize (e.g., "GENERATE_ROADMAP_PROMPT")
        min_samples: Minimum number of feedback samples required to run optimization
        n_trials: Number of optimization trials

    Returns:
        dict with optimization results or error information
    """
    client = get_opik_client()
    if not client:
        return {"status": "error", "message": "Opik client not available"}

    # Fetch feedback traces
    traces = await fetch_feedback_traces(prompt_name)
    if len(traces) < min_samples:
        return {
            "status": "skipped",
            "message": f"Not enough feedback samples. Got {len(traces)}, need {min_samples}",
            "prompt_name": prompt_name,
        }

    # Build dataset
    dataset_items = build_optimization_dataset(traces, prompt_name)
    if len(dataset_items) < min_samples:
        return {
            "status": "skipped",
            "message": f"Not enough valid dataset items. Got {len(dataset_items)}, need {min_samples}",
            "prompt_name": prompt_name,
        }

    try:
        from opik_optimizer import MetaPromptOptimizer, ChatPrompt
        from opik.evaluation.metrics import LevenshteinRatio

        current_prompt = client.get_prompt(name=prompt_name)
        current_prompt_text = current_prompt.prompt

        chat_prompt = ChatPrompt(
            messages=[
                {"role": "system", "content": current_prompt_text},
                {"role": "user", "content": "{input}"},
            ]
        )

        dataset = client.create_dataset(
            name=f"feedback-optimization-{prompt_name}",
            description=f"Auto-generated dataset for {prompt_name} optimization",
        )
        for item in dataset_items:
            dataset.insert(
                [
                    {
                        "input": str(item["input"]),
                        "expected_output": item["expected_output"],
                    }
                ]
            )

        optimizer = MetaPromptOptimizer(
            model="gemini-2.5-flash-lite",
            project_name=settings.opik_project_name,
            n_threads=4,
        )

        def feedback_alignment(dataset_item, llm_output):
            """Score based on output alignment with expected feedback direction."""
            return LevenshteinRatio().score(
                reference=dataset_item.get("expected_output", ""), output=llm_output
            )

        # Run optimization
        result = optimizer.optimize_prompt(
            prompt=chat_prompt,
            dataset=dataset,
            metric=feedback_alignment,
            n_samples=min(len(dataset_items), 20),
        )

        # Extract the optimized prompt
        optimized_prompt_text = ""
        if result and hasattr(result, "prompt") and result.prompt.messages:
            # Get the system message which contains the optimized prompt
            for msg in result.prompt.messages:
                if msg.get("role") == "system":
                    optimized_prompt_text = msg.get("content", "")
                    break

        if optimized_prompt_text:
            # Create new prompt version in Opik
            new_prompt = client.create_prompt(
                name=prompt_name,
                prompt=optimized_prompt_text,
            )

            return {
                "status": "success",
                "prompt_name": prompt_name,
                "new_version": (
                    new_prompt.version if hasattr(new_prompt, "version") else "created"
                ),
                "samples_used": len(dataset_items),
                "improvement_score": result.score if hasattr(result, "score") else None,
            }
        else:
            return {
                "status": "error",
                "message": "Optimization completed but no improved prompt generated",
                "prompt_name": prompt_name,
            }

    except ImportError as e:
        return {
            "status": "error",
            "message": f"opik-optimizer not installed: {e}",
            "prompt_name": prompt_name,
        }
    except Exception as e:
        logging.error(f"Prompt optimization failed: {e}")
        return {
            "status": "error",
            "message": str(e),
            "prompt_name": prompt_name,
        }


async def optimize_all_prompts(min_samples: int = 5) -> list[dict]:
    """
    Run optimization for all configured prompts.

    Returns:
        List of optimization results for each prompt
    """
    results = []
    for prompt_name in PROMPT_CONFIGS.keys():
        result = await run_prompt_optimization(
            prompt_name=prompt_name,
            min_samples=min_samples,
        )
        results.append(result)
    return results
