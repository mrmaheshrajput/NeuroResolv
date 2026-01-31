import json

from app.config import get_settings
from app.observability import track_llm_call
from google import genai
from google.genai import types

settings = get_settings()
client = genai.Client(api_key=settings.google_api_key)


RECOVERY_SYSTEM_PROMPT = """You are an expert learning coach who helps learners recover from failed quizzes.

When a learner fails a verification quiz, you:
1. Analyze what concepts they struggled with
2. Suggest specific review strategies
3. Recommend adjusted approaches for the next session
4. Provide encouragement while being honest about gaps

Return JSON:
{
  "analysis": "What went wrong and why",
  "weak_concepts": ["concept1", "concept2"],
  "review_strategies": [
    {
      "concept": "concept name",
      "strategy": "How to review this",
      "resources": "Suggested resources or approaches"
    }
  ],
  "next_session_focus": "What to focus on next time",
  "encouragement": "Motivational message",
  "should_revisit_milestone": true/false
}"""


@track_llm_call("failure_recovery")
async def analyze_failure_and_suggest_recovery(
    quiz_results: dict,
    original_content: str,
    current_milestone: dict,
    goal_context: str,
) -> dict:
    prompt = f"""A learner failed their verification quiz. Help them recover.

QUIZ RESULTS:
Overall Score: {quiz_results.get('overall_score', 0) * 100:.0f}%
Summary: {quiz_results.get('summary_feedback', 'No feedback available')}
Concepts to Reinforce: {', '.join(quiz_results.get('concepts_to_reinforce', []))}

WHAT THEY STUDIED: {original_content[:500]}

CURRENT MILESTONE: {current_milestone.get('title', 'Unknown')}
Milestone Goal: {current_milestone.get('verification_criteria', 'Not specified')}

OVERALL GOAL: {goal_context}

Provide recovery strategies and next steps."""

    try:
        response = await client.aio.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=RECOVERY_SYSTEM_PROMPT,
                temperature=0.6,
                response_mime_type="application/json",
            ),
        )

        return json.loads(response.text)

    except Exception:
        return {
            "analysis": "Unable to analyze specifics, but continued practice will help.",
            "weak_concepts": quiz_results.get("concepts_to_reinforce", []),
            "review_strategies": [
                {
                    "concept": "general",
                    "strategy": "Review the material again with focus on explaining concepts out loud",
                    "resources": "Re-read the source material and take notes",
                }
            ],
            "next_session_focus": "Spend extra time on the concepts you struggled with",
            "encouragement": "Learning takes time! Every attempt makes you stronger.",
            "should_revisit_milestone": False,
        }


REFLECTION_SYSTEM_PROMPT = """You are a thoughtful learning coach who generates weekly reflection prompts.

Create prompts that help learners:
1. Celebrate their progress
2. Identify what worked well
3. Recognize challenges and how they overcame them
4. Connect their learning to their bigger goal
5. Set intentions for the coming week

Return JSON:
{
  "prompt": "The reflection prompt question",
  "sub_prompts": ["Optional follow-up questions"]
}"""


@track_llm_call("weekly_reflection")
async def generate_weekly_reflection_prompt(
    week_number: int,
    goal_context: str,
    logs_this_week: list[dict],
    milestone_progress: dict,
) -> dict:
    logs_summary = (
        "\n".join(
            [
                f"- {log.get('date')}: {log.get('content')[:100]}..."
                for log in logs_this_week
            ]
        )
        if logs_this_week
        else "No logs this week"
    )

    prompt = f"""Generate a personalized weekly reflection prompt.

WEEK NUMBER: {week_number}
GOAL: {goal_context}

ACTIVITY THIS WEEK:
{logs_summary}

MILESTONE PROGRESS:
Current: {milestone_progress.get('current', 'N/A')}
Completed: {milestone_progress.get('completed', 0)} of {milestone_progress.get('total', '?')}

Create a thoughtful reflection prompt for this specific week."""

    try:
        response = await client.aio.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=REFLECTION_SYSTEM_PROMPT,
                temperature=0.7,
                response_mime_type="application/json",
            ),
        )

        return json.loads(response.text)

    except Exception:
        prompts_by_week = [
            "What was your biggest breakthrough this week? What made it click?",
            "What challenged you most this week, and how did you handle it?",
            "How has your understanding evolved compared to when you started?",
            "What would you teach someone who's just starting this journey?",
        ]
        return {
            "prompt": prompts_by_week[(week_number - 1) % len(prompts_by_week)],
            "sub_prompts": [],
        }
