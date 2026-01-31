"""North Star Agent - Generates end-of-year vision and transformation goals.

This agent creates inspiring long-term goals that focus on personal transformation
and habit formation, not just task completion.
"""

import json
from datetime import datetime

from app.config import get_settings
from app.observability import get_learning_analytics, track_llm_call
from google import genai
from google.genai import types

settings = get_settings()
client = genai.Client(api_key=settings.google_api_key)


NORTH_STAR_SYSTEM_PROMPT = """You are a life coach who helps people envision their best selves.

Your task is to generate an inspiring "North Star" goal - a vision of who the person will become by the end of the year through their resolution journey.

This is NOT about completing tasks. This is about TRANSFORMATION and BECOMING.

Key principles:
1. Focus on the PERSON they'll become, not the tasks they'll complete
2. Emphasize habit formation and lifestyle change
3. Connect the resolution to broader life improvements
4. Be inspiring but realistic - grounded in their starting point
5. Paint a vivid picture of their future self
6. Include the identity shift (e.g., "I am a reader" not "I read books")

Return a JSON object with this structure:
{
  "north_star_statement": "A vivid, inspiring 2-3 sentence description of who they'll become",
  "key_transformations": ["3-4 specific ways their life will be different"],
  "identity_shift": "The new identity they'll embody (e.g., 'I am a confident Spanish speaker')",
  "why_it_matters": "1 sentence on the deeper meaning of this transformation"
}"""


REGENERATION_SYSTEM_PROMPT = """You are a life coach who helps people envision their best selves.

The user didn't connect with the previous North Star goal. Their feedback was provided.
Generate a NEW vision that resonates better with their aspirations.

Maybe the previous one was:
- Too ambitious or not ambitious enough
- Too vague or too specific
- Not aligned with their actual motivation
- Missing the emotional connection

Address their concerns and create a vision they'll be excited to pursue.

Return a JSON object with this structure:
{
  "north_star_statement": "A vivid, inspiring 2-3 sentence description of who they'll become",
  "key_transformations": ["3-4 specific ways their life will be different"],
  "identity_shift": "The new identity they'll embody",
  "why_it_matters": "1 sentence on the deeper meaning of this transformation"
}"""


@track_llm_call("north_star_generation")
async def generate_north_star(
    resolution_goal: str,
    category: str,
    resolution_id: int | None = None,
    skill_level: str | None = None,
    milestones: list[dict] | None = None,
    progress_summary: str | None = None,
) -> dict:
    """Generate a North Star goal for a resolution.

    Now incorporates learning analytics from Opik if resolution_id is provided.
    """
    # Build milestones context
    milestones_context = ""
    if milestones:
        milestone_titles = [m.get("title", "") for m in milestones[:5]]
        milestones_context = f"\nTheir learning roadmap includes:\n" + "\n".join(
            f"- {title}" for title in milestone_titles
        )

    # Fetch rich context from Opik if possible
    opik_context = ""
    if resolution_id:
        analytics = await get_learning_analytics(resolution_id)
        if analytics.get("status") != "no_data":
            mastered = analytics.get("mastered_concepts", [])
            avg_score = analytics.get("avg_quiz_score", 0)

            opik_context = f"\nOPIK TRANSFORMATION CONTEXT:\n"
            opik_context += f"- Current Mastery Level: {avg_score*100:.1f}%\n"
            if mastered:
                opik_context += (
                    f"- Demonstrated competency in: {', '.join(mastered[:5])}\n"
                )

    # Current year's end
    current_year_end = datetime(datetime.now().year, 12, 31).strftime("%B %d, %Y")

    prompt = f"""Create a North Star goal for this person:

THEIR RESOLUTION: {resolution_goal}
CATEGORY: {category}
CURRENT LEVEL: {skill_level or "Beginning their journey"}
{milestones_context}
{opik_context}

TARGET DATE: {current_year_end}
{f"PROGRESS SO FAR: {progress_summary}" if progress_summary else ""}

Generate an inspiring vision of who they'll become by the end of the year.
Focus on transformation and identity, not tasks completed.
Use the OPIK context to see where they are already showing mastery and push them towards a stronger identity in those areas."""

    try:
        response = await client.aio.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=NORTH_STAR_SYSTEM_PROMPT,
                temperature=0.8,  # Slightly higher for more creative output
                response_mime_type="application/json",
            ),
        )

        result = json.loads(response.text)
        return result

    except Exception as e:
        return _generate_fallback_north_star(resolution_goal, category)


@track_llm_call("north_star_regeneration")
async def regenerate_north_star_with_feedback(
    resolution_goal: str,
    category: str,
    original_north_star: str,
    feedback_text: str,
    skill_level: str | None = None,
) -> dict:
    """Regenerate a North Star goal using gemini-2.5-pro after negative feedback.

    Uses a more capable model to create a vision that truly resonates.
    """
    prompt = f"""The user didn't connect with this North Star vision:
ORIGINAL: {original_north_star}

USER FEEDBACK: {feedback_text}

Create a BETTER North Star for this resolution:

RESOLUTION: {resolution_goal}
CATEGORY: {category}
CURRENT LEVEL: {skill_level or "Beginning their journey"}

Address their concerns and create a vision they'll be excited about."""

    try:
        response = await client.aio.models.generate_content(
            model="gemini-2.5-pro",  # Use pro model for regeneration
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=REGENERATION_SYSTEM_PROMPT,
                temperature=0.8,
                response_mime_type="application/json",
            ),
        )

        result = json.loads(response.text)
        return result

    except Exception as e:
        return _generate_fallback_north_star(resolution_goal, category)


def _generate_fallback_north_star(goal: str, category: str) -> dict:
    """Fallback north star if AI generation fails."""
    category_identities = {
        "learning": "lifelong learner",
        "reading": "dedicated reader",
        "skill": "skilled practitioner",
        "fitness": "active and healthy person",
        "professional": "confident professional",
        "creative": "creative individual",
    }

    identity = category_identities.get(category, "transformed individual")

    return {
        "north_star_statement": f"By year's end, you'll have built the habits and knowledge that make you a {identity}. The daily practice will feel natural, and the results will be undeniable.",
        "key_transformations": [
            "You'll have overcome initial resistance and built consistency",
            "Your knowledge and skills will have compounded significantly",
            "You'll see yourself differently - as someone who does this",
            "Others will notice and ask about your journey",
        ],
        "identity_shift": f"I am a {identity} who shows up consistently",
        "why_it_matters": "This journey is about becoming the person who naturally achieves goals like this.",
    }


async def update_north_star_from_progress(
    resolution_goal: str,
    category: str,
    current_north_star: dict,
    progress_percentage: float,
    key_achievements: list[str],
) -> dict:
    """Update North Star based on significant progress.

    Called when user has made substantial progress and the vision might need updating.
    """
    if progress_percentage < 50:
        # Not enough progress to warrant an update
        return current_north_star

    prompt = f"""The user has made significant progress on their resolution:

RESOLUTION: {resolution_goal}
PROGRESS: {progress_percentage}% complete
KEY ACHIEVEMENTS: {', '.join(key_achievements[:5])}

CURRENT NORTH STAR: {current_north_star.get('north_star_statement', '')}

Should the North Star be updated to reflect their growth?
If yes, provide an updated vision. If no, return the same vision with "updated": false.

Return JSON with the North Star structure plus an "updated" boolean field."""

    try:
        response = await client.aio.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=NORTH_STAR_SYSTEM_PROMPT,
                temperature=0.6,
                response_mime_type="application/json",
            ),
        )

        result = json.loads(response.text)
        return result

    except Exception:
        return {**current_north_star, "updated": False}
