"""Weekly Goal Agent - Generates near-term actionable goals for users.

This agent creates focused weekly goals based on the user's resolutions,
considering their cadence, recent progress, and other active resolutions.
"""

import json
from datetime import datetime, timedelta

from app.config import get_settings
from app.observability import get_learning_analytics, track_llm_call
from google import genai
from google.genai import types

settings = get_settings()
client = genai.Client(api_key=settings.google_api_key)


WEEKLY_GOAL_SYSTEM_PROMPT = """You are a motivational coach who creates focused, achievable weekly goals.

Your task is to generate a single, clear goal for the upcoming week that helps the user make meaningful progress on their resolution.

Rules:
1. The goal should be achievable within 7 days regardless of the user's cadence
2. Consider the user's current skill level and recent progress
3. If the user has multiple resolutions, balance time commitment across them
4. Be specific and actionable - avoid vague goals
5. The goal should feel motivating, not overwhelming
6. Focus on the process/habit, not just the outcome

Return a JSON object with this structure:
{
  "goal_text": "A clear, actionable weekly goal (1-2 sentences)",
  "micro_actions": ["3-5 small daily actions that support this goal"],
  "motivation_note": "A brief encouraging message (1 sentence)"
}"""


REGENERATION_SYSTEM_PROMPT = """You are a motivational coach who creates focused, achievable weekly goals.

The user didn't like the previous suggestion. Their feedback was provided.
Generate a NEW, improved goal that addresses their concerns.

Be more specific, more realistic, or adjust the difficulty based on their feedback.
Consider what they explicitly mentioned as problems.

Return a JSON object with this structure:
{
  "goal_text": "A clear, actionable weekly goal (1-2 sentences)",
  "micro_actions": ["3-5 small daily actions that support this goal"],
  "motivation_note": "A brief encouraging message (1 sentence)"
}"""


AGGREGATED_FOCUS_SYSTEM_PROMPT = """You are a high-performance productivity coach.
Your task is to generate a single, cohesive weekly focus statement for a user who has multiple learning resolutions.

Rules:
1. Create a single "Combined Focus" statement (1-2 sentences) that weaves together themes from all active resolutions.
2. Provide 3-5 "Integrated Micro-actions" that help the user make progress on ALL resolutions during the week without feeling overwhelmed.
3. Balance the time commitment – avoid suggesting 7 days of intense work for all resolutions.
4. Focus on the synergy between the goals (e.g., "This week, we're building the habit of deep focus, which will help with both your Spanish and Python goals").
5. The tone should be inspiring, holistic, and realistic.

Return a JSON object with this structure:
{
  "focus_text": "The combined weekly focus statement",
  "micro_actions": ["Action 1", "Action 2", ...],
  "motivation_note": "A summary word of encouragement"
}"""


@track_llm_call("weekly_goal_generation")
async def generate_weekly_goal(
    resolution_goal: str,
    category: str,
    cadence: str,
    resolution_id: int | None = None,
    skill_level: str | None = None,
    recent_progress: list[dict] | None = None,
    other_resolutions: list[dict] | None = None,
) -> dict:
    """Generate a weekly goal for a resolution.

    Now incorporates learning analytics from Opik if resolution_id is provided.
    """
    cadence_map = {
        "daily": "7 days/week",
        "3x_week": "3 times per week",
        "weekdays": "5 days/week (Mon-Fri)",
        "weekly": "1 day per week",
    }
    cadence_description = cadence_map.get(cadence, "regularly")

    # Fetch rich context from Opik if possible
    learning_context = ""
    if resolution_id:
        analytics = await get_learning_analytics(resolution_id)
        if analytics.get("status") != "no_data":
            mastered = analytics.get("mastered_concepts", [])
            weak = analytics.get("weak_concepts", [])
            avg_score = analytics.get("avg_quiz_score", 0)

            learning_context = f"\nLEARNING ANALYTICS (from Opik traces):\n"
            learning_context += f"- Average Quiz Score: {avg_score*100:.1f}%\n"
            if mastered:
                learning_context += f"- Mastered Concepts: {', '.join(mastered[:5])}\n"
            if weak:
                learning_context += (
                    f"- Weak Concepts (NEEDS FOCUS): {', '.join(weak[:5])}\n"
                )

    # Build progress context
    progress_context = ""
    if recent_progress:
        recent_logs = recent_progress[:5]  # Last 5 logs
        log_summaries = [log.get("content", "")[:100] for log in recent_logs]
        progress_context = f"\nRecent progress logs:\n" + "\n".join(
            f"- {log}" for log in log_summaries
        )

    # Build other resolutions context
    other_context = ""
    if other_resolutions:
        other_context = (
            f"\nOther active resolutions (consider time balance):\n"
            + "\n".join(
                f"- {r.get('goal_statement', '')[:50]}... ({r.get('cadence', 'daily')})"
                for r in other_resolutions
            )
        )

    prompt = f"""Create a weekly goal for this resolution:

MAIN GOAL: {resolution_goal}
CATEGORY: {category}
SKILL LEVEL: {skill_level or "Not specified"}
COMMITMENT: {cadence_description}
{learning_context}
{progress_context}
{other_context}

Generate an achievable weekly goal that moves the user towards their main goal.
If there are weak concepts, try to incorporate them into this week's focus.
The goal should be completable within this week and feel motivating."""

    try:
        response = await client.aio.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=WEEKLY_GOAL_SYSTEM_PROMPT,
                temperature=0.7,
                response_mime_type="application/json",
            ),
        )

        result = json.loads(response.text)
        return result

    except Exception as e:
        return _generate_fallback_weekly_goal(resolution_goal, cadence)


@track_llm_call("weekly_goal_regeneration")
async def regenerate_weekly_goal_with_feedback(
    resolution_goal: str,
    category: str,
    cadence: str,
    original_goal: str,
    feedback_text: str,
    skill_level: str | None = None,
) -> dict:
    """Regenerate a weekly goal using gemini-2.5-pro after negative feedback.

    Uses a more capable model to address user's specific concerns.
    """
    prompt = f"""The user didn't like this weekly goal suggestion:
ORIGINAL GOAL: {original_goal}

USER FEEDBACK: {feedback_text}

Create a BETTER weekly goal for this resolution:

MAIN GOAL: {resolution_goal}
CATEGORY: {category}
SKILL LEVEL: {skill_level or "Not specified"}
COMMITMENT: {cadence}

Address the user's concerns and generate an improved goal."""

    try:
        response = await client.aio.models.generate_content(
            model="gemini-2.5-pro",  # Use pro model for regeneration
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=REGENERATION_SYSTEM_PROMPT,
                temperature=0.7,
                response_mime_type="application/json",
            ),
        )

        result = json.loads(response.text)
        return result

    except Exception as e:
        return _generate_fallback_weekly_goal(resolution_goal, cadence)


def _generate_fallback_weekly_goal(goal: str, cadence: str) -> dict:
    """Fallback goal if AI generation fails."""
    if cadence == "daily":
        micro_actions = [
            "Dedicate 15-30 minutes each day",
            "Track your progress in a journal",
            "Review what you learned before bed",
        ]
    elif cadence == "weekly":
        micro_actions = [
            "Block 1-2 hours for focused work",
            "Set a specific day and time",
            "Prepare materials in advance",
        ]
    else:
        micro_actions = [
            "Set aside focused time on scheduled days",
            "Review progress mid-week",
            "Celebrate small wins",
        ]

    return {
        "goal_text": f"This week, make meaningful progress on: {goal[:100]}...",
        "micro_actions": micro_actions,
        "motivation_note": "Every step forward counts. You've got this!",
    }


async def get_aggregated_weekly_focus(
    resolutions: list[dict],
) -> dict:
    """Generate a cohesive combined weekly focus for users with multiple resolutions."""
    if not resolutions:
        return {
            "focus_text": "No active resolutions to focus on this week.",
            "micro_actions": [],
            "motivation_note": "Create your first resolution to get started!",
        }

    # Prepare context for the LLM
    resolutions_context = []
    for res in resolutions:
        res_info = (
            f"- Goal: {res.get('goal_statement')}\n"
            f"  Category: {res.get('category')}\n"
            f"  Cadence: {res.get('cadence')}\n"
            f"  Skill Level: {res.get('skill_level')}\n"
        )
        resolutions_context.append(res_info)

    prompt = f"""Generate a combined weekly focus for a user with these active resolutions:

{chr(10).join(resolutions_context)}

Create a unified strategy that helps them progress on all these goals in a balanced way this week."""

    try:
        response = await client.aio.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=AGGREGATED_FOCUS_SYSTEM_PROMPT,
                temperature=0.7,
                response_mime_type="application/json",
            ),
        )

        return json.loads(response.text)

    except Exception as e:
        # Fallback
        res_count = len(resolutions)
        return {
            "focus_text": f"This week, let's find a healthy rhythm across your {res_count} goals.",
            "micro_actions": [
                "Schedule specific time blocks for each goal",
                "Start with the goal that feels most exciting today",
                "Keep your daily check-in streak alive",
            ],
            "motivation_note": "Consistency is your greatest superpower.",
        }
