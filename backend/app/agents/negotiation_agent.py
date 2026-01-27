import json
from google import genai
from google.genai import types

from app.config import get_settings
from app.observability import track_llm_call


settings = get_settings()
client = genai.Client(api_key=settings.google_api_key)


NEGOTIATION_SYSTEM_PROMPT = """You are a behavioral scientist and learning coach specialized in habit formation and goal setting.
Your task is to perform a 'Reality Check' on a user's proposed learning resolution.

Analyze the feasibility of the goal based on:
1. Goal Statement: What they want to achieve.
2. Skill Level: Their current expertise.
3. Cadence: How often they plan to work on it.

Rules for your analysis:
- Be encouraging but realistic.
- Identify potential burn-out risks (e.g., Beginners selecting 'Daily' for difficult skills like coding or languages).
- If a plan seems too ambitious for a beginner, suggest a more sustainable starting point (e.g., 3x/week instead of Daily).
- Use data-driven insights if possible (e.g., '80% of people burn out in Week 2 with this schedule').
- Keep the tone friendly and supportive, like a mentor.

Return a JSON object with this structure:
{
  "is_feasible": true|false,
  "feedback": "A short, impactful explanation of why it is or isn't feasible and what the risks are.",
  "suggestion": {
    "cadence": "daily|3x_week|weekdays|weekly",
    "reason": "Why this specific cadence is better."
  },
  "streak_trigger": "e.g., 2-week streak"
}"""


@track_llm_call("resolution_negotiation")
async def analyze_feasibility(
    goal_statement: str,
    category: str,
    skill_level: str | None,
    cadence: str,
) -> dict:
    prompt = f"""Perform a Reality Check on this resolution:

GOAL: {goal_statement}
CATEGORY: {category}
SKILL LEVEL: {skill_level or "Beginner (assumed)"}
CADENCE: {cadence}

Is this realistic? If not, what would you suggest instead to ensure they don't burn out and actually achieve the goal?"""

    try:
        response = await client.aio.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=NEGOTIATION_SYSTEM_PROMPT,
                temperature=0.7,
                response_mime_type="application/json",
            ),
        )
        
        return json.loads(response.text)
        
    except Exception as e:
        # Fallback if LLM fails
        return {
            "is_feasible": True,
            "feedback": "Your plan looks solid! Consistency is key.",
            "suggestion": None,
            "streak_trigger": "2-week streak"
        }
