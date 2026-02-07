"""
API endpoint for prompt optimization.

This endpoint is triggered by a Lambda function to run MetaPromptOptimizer
on prompts that have received negative feedback.
"""

from fastapi import APIRouter

from app.observability import optimize_all_prompts, run_prompt_optimization

router = APIRouter(prefix="/system", tags=["system"])


@router.post("/optimize-prompts")
async def optimize_prompts(
    prompt_name: str | None = None,
    min_samples: int = 5,
):
    """
    Run prompt optimization using MetaPromptOptimizer.

    This endpoint is designed to be called by a Lambda function on a schedule.
    It collects feedback traces from Opik, builds a dataset, and runs
    MetaPromptOptimizer to create improved prompt versions.

    Args:
        prompt_name: Optional specific prompt to optimize. If None, optimizes all.
        min_samples: Minimum number of feedback samples required (default: 5)
    """
    if prompt_name:
        result = await run_prompt_optimization(
            prompt_name=prompt_name,
            min_samples=min_samples,
        )
        return {"results": [result]}
    else:
        results = await optimize_all_prompts(min_samples=min_samples)
        return {"results": results}
