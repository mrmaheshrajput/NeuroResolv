import json
from datetime import datetime, timedelta
from google import genai
from google.genai import types

from app.config import get_settings
from app.observability import track_llm_call


settings = get_settings()
client = genai.Client(api_key=settings.google_api_key)


ROADMAP_SYSTEM_PROMPT = """You are an expert learning architect who creates personalized milestone-based roadmaps.

Your task is to generate a learning roadmap with milestones based on the user's goal, skill level, cadence, and learning sources.

Rules:
1. Create 4-12 milestones depending on the goal complexity
2. Each milestone should be achievable within 1-4 weeks
3. Include clear verification criteria for each milestone
4. Verification criteria should be things the learner can demonstrate (explain, apply, create)
5. Consider the user's current skill level when setting expectations
6. Adapt the number of milestones based on cadence (weekly = more spread out, daily = denser)

Return a JSON object with this structure:
{
  "milestones": [
    {
      "order": 1,
      "title": "Foundation: Understanding Core Concepts",
      "description": "What this milestone covers and why it matters",
      "verification_criteria": "Be able to explain X in your own words / Create Y / Demonstrate Z",
      "estimated_weeks": 2
    }
  ],
  "skill_assessment": "beginner|intermediate|advanced",
  "total_estimated_weeks": 12
}"""


@track_llm_call("roadmap_generation")
async def generate_roadmap(
    goal_statement: str,
    category: str,
    skill_level: str | None,
    cadence: str,
    learning_sources: list[dict],
) -> dict:
    sources_text = ""
    if learning_sources:
        source_items = []
        for source in learning_sources:
            if source.get("type") == "book":
                source_items.append(f"Book: {source.get('title', 'Unknown')}")
            elif source.get("type") == "url":
                source_items.append(
                    f"Online Resource: {source.get('value', 'Unknown')}"
                )
            elif source.get("type") == "youtube":
                source_items.append(f"YouTube: {source.get('value', 'Unknown')}")
            elif source.get("type") == "course":
                source_items.append(f"Course: {source.get('value', 'Unknown')}")
        sources_text = "\n".join(source_items)
    else:
        sources_text = (
            "No specific sources provided - user will find resources as they go"
        )

    cadence_map = {
        "daily": "Learning daily (7 days/week)",
        "3x_week": "Learning 3 times per week",
        "weekdays": "Learning on weekdays only (5 days/week)",
        "weekly": "Learning once per week",
    }
    cadence_description = cadence_map.get(cadence, "Learning regularly")

    prompt = f"""Create a personalized learning roadmap for this goal:

GOAL: {goal_statement}

CATEGORY: {category}

CURRENT SKILL LEVEL: {skill_level or "Not specified - please assess from the goal"}

LEARNING CADENCE: {cadence_description}

LEARNING SOURCES:
{sources_text}

Generate a milestone-based roadmap that will guide this learner to achieve their goal.
Each milestone should have clear, demonstrable verification criteria."""

    try:
        response = await client.aio.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=ROADMAP_SYSTEM_PROMPT,
                temperature=0.7,
                response_mime_type="application/json",
            ),
        )

        result = json.loads(response.text)
        return result

    except Exception as e:
        return _generate_fallback_roadmap(goal_statement, category, cadence)


def _generate_fallback_roadmap(goal: str, category: str, cadence: str) -> dict:
    weeks_per_milestone = (
        2 if cadence == "daily" else 3 if cadence in ["3x_week", "weekdays"] else 4
    )

    return {
        "milestones": [
            {
                "order": 1,
                "title": "Foundation: Getting Started",
                "description": f"Build foundational understanding of {goal[:50]}",
                "verification_criteria": "Explain the core concepts in your own words",
                "estimated_weeks": weeks_per_milestone,
            },
            {
                "order": 2,
                "title": "Building Knowledge",
                "description": "Deepen understanding with active practice",
                "verification_criteria": "Apply concepts to a simple example or scenario",
                "estimated_weeks": weeks_per_milestone,
            },
            {
                "order": 3,
                "title": "Intermediate Application",
                "description": "Connect concepts and build practical skills",
                "verification_criteria": "Complete a small project or demonstrate integrated understanding",
                "estimated_weeks": weeks_per_milestone,
            },
            {
                "order": 4,
                "title": "Advanced Mastery",
                "description": "Achieve fluency and deeper expertise",
                "verification_criteria": "Teach the concepts to someone else or create something original",
                "estimated_weeks": weeks_per_milestone,
            },
        ],
        "skill_assessment": "beginner",
        "total_estimated_weeks": weeks_per_milestone * 4,
    }


@track_llm_call("milestone_refinement")
async def refine_milestone(
    milestone_title: str,
    user_edit: dict,
    context: str,
) -> dict:
    prompt = f"""The user has edited a milestone in their learning roadmap.

Original Milestone: {milestone_title}
User's Changes: {json.dumps(user_edit)}
Goal Context: {context}

Ensure the edited milestone still makes sense and suggest any improvements if needed.
Return JSON with: {{"refined_title": "...", "refined_description": "...", "refined_criteria": "...", "suggestion": "optional note"}}"""

    try:
        response = await client.aio.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.5,
                response_mime_type="application/json",
            ),
        )
        return json.loads(response.text)
    except Exception:
        return user_edit
