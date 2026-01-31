import json
from datetime import datetime, timedelta

from app.config import get_settings
from app.observability import get_learning_analytics, track_llm_call
from google import genai
from google.genai import types

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
) -> dict:
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


LIVING_ROADMAP_SYSTEM_PROMPT = """You are an adaptive learning coach who adjusts roadmaps based on user progress.

Your task is to review the user's progress and suggest updates to their learning roadmap.

Rules:
1. Preserve completed milestones - don't change what's done
2. Adjust remaining milestones based on actual progress speed
3. If user is ahead, can suggest adding depth or advanced topics
4. If user is behind, suggest simplifying or extending timelines
5. Always maintain motivation - frame adjustments positively
6. Consider quiz scores and verification data in adjustments

Return a JSON object with:
{
  "adjustments": [{
    "milestone_order": 2,
    "adjustment_type": "modify|remove|add",
    "reason": "Why this change",
    "updated_milestone": {...} // if modify or add
  }],
  "overall_assessment": "On track|Ahead|Needs adjustment",
  "encouragement": "Motivational message based on progress"
}"""


@track_llm_call("living_roadmap_refresh")
async def generate_living_roadmap_update(
    goal_statement: str,
    category: str,
    cadence: str,
    current_milestones: list[dict],
    progress_logs: list[dict],
    streak_data: dict,
    resolution_id: int | None = None,
    verification_scores: list[float] | None = None,
) -> dict:
    """Generate a living roadmap update based on user's actual progress.

    Now incorporates learning analytics from Opik if resolution_id is provided.
    """
    milestone_summary = []
    for m in current_milestones:
        status = m.get("status", "pending")
        milestone_summary.append(
            f"- [{status}] {m.get('title', 'Untitled')}: {m.get('description', '')[:100]}"
        )

    progress_summary = ""
    if progress_logs:
        recent_logs = progress_logs[:10]
        log_entries = [f"- {log.get('content', '')[:80]}..." for log in recent_logs]
        progress_summary = "\n".join(log_entries)

    # Fetch rich context from Opik if possible
    opik_context = ""
    if resolution_id:
        analytics = await get_learning_analytics(resolution_id)
        if analytics.get("status") != "no_data":
            mastered = analytics.get("mastered_concepts", [])
            weak = analytics.get("weak_concepts", [])
            avg_score = analytics.get("avg_quiz_score", 0)

            opik_context = f"\nOPIK LEARNING CONTEXT:\n"
            opik_context += f"- Historical Avg Quiz Score: {avg_score*100:.1f}%\n"
            if mastered:
                opik_context += f"- Mastered so far: {', '.join(mastered[:5])}\n"
            if weak:
                opik_context += f"- Weak areas: {', '.join(weak[:5])}\n"

    verification_context = ""
    if verification_scores:
        avg_score = sum(verification_scores) / len(verification_scores)
        verification_context = f"\nRecent quiz scores average: {avg_score:.1%}"

    prompt = f"""Review and update this learning roadmap:

GOAL: {goal_statement}
CATEGORY: {category}
CADENCE: {cadence}

CURRENT MILESTONES:
{chr(10).join(milestone_summary)}

RECENT PROGRESS:
{progress_summary}
{opik_context}
{verification_context}

STREAK: {streak_data.get('current_streak', 0)} days (longest: {streak_data.get('longest_streak', 0)})

Analyze the progress and suggest any roadmap adjustments needed.
If there are persistent weak areas in the OPIK context, adjust future milestones to reinforce those concepts."""

    try:
        response = await client.aio.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=LIVING_ROADMAP_SYSTEM_PROMPT,
                temperature=0.6,
                response_mime_type="application/json",
            ),
        )

        result = json.loads(response.text)
        return result

    except Exception as e:
        return {
            "adjustments": [],
            "overall_assessment": "On track",
            "encouragement": "Keep up the great work!",
        }


def calculate_goal_likelihood_score(
    streak_data: dict,
    milestones: list[dict],
    progress_logs: list[dict],
    verification_scores: list[float] | None = None,
) -> float:
    """Calculate the likelihood of achieving the goal (0.0 to 1.0).

    Factors:
    - Streak consistency (weight: 30%)
    - Milestone completion rate (weight: 30%)
    - Check-in frequency (weight: 20%)
    - Verification scores (weight: 20%)
    """
    score = 0.0

    current_streak = streak_data.get("current_streak", 0)
    longest_streak = streak_data.get("longest_streak", 1)
    streak_ratio = min(current_streak / max(longest_streak, 7), 1.0)
    score += 0.3 * streak_ratio

    completed = len([m for m in milestones if m.get("status") == "completed"])
    total = len(milestones) or 1
    milestone_ratio = completed / total
    score += 0.3 * milestone_ratio

    recent_logs = len([log for log in progress_logs if log])
    expected_logs = 7  # Expect at least 7 logs for engaged user
    frequency_ratio = min(recent_logs / expected_logs, 1.0)
    score += 0.2 * frequency_ratio

    # Verification scores (20%)
    if verification_scores and len(verification_scores) > 0:
        avg_score = sum(verification_scores) / len(verification_scores)
        score += 0.2 * avg_score
    else:
        # No verification data - assume neutral (0.5)
        score += 0.2 * 0.5

    return round(score, 2)


def calculate_next_refresh_date(
    cadence: str, last_refresh: datetime | None = None
) -> datetime:
    """Calculate when the next roadmap refresh should occur.

    Refresh frequency based on cadence:
    - daily: Every 1 week
    - 3x_week/weekdays: Every 2 weeks
    - weekly: Every 4 weeks (1 month max)
    """
    now = datetime.utcnow()
    base_date = last_refresh or now

    refresh_intervals = {
        "daily": timedelta(weeks=1),
        "3x_week": timedelta(weeks=2),
        "weekdays": timedelta(weeks=2),
        "weekly": timedelta(weeks=4),
    }

    interval = refresh_intervals.get(cadence, timedelta(weeks=2))
    next_refresh = base_date + interval

    # Ensure it's in the future
    if next_refresh <= now:
        next_refresh = now + interval

    return next_refresh


@track_llm_call("roadmap_regeneration")
async def regenerate_roadmap_with_feedback(
    goal_statement: str,
    category: str,
    skill_level: str | None,
    cadence: str,
    original_roadmap: dict,
    feedback_text: str,
) -> dict:
    """Regenerate roadmap using gemini-2.5-pro after negative feedback.

    Args:
        goal_statement: The main goal
        category: Category of resolution
        skill_level: User's skill level
        cadence: User's cadence
        original_roadmap: The roadmap that was rejected
        feedback_text: User's feedback on what they didn't like
    """
    original_titles = [
        m.get("title", "") for m in original_roadmap.get("milestones", [])
    ]

    prompt = f"""The user didn't like this roadmap:
ORIGINAL MILESTONES: {', '.join(original_titles)}

USER FEEDBACK: {feedback_text}

Create a BETTER roadmap for:
GOAL: {goal_statement}
CATEGORY: {category}
SKILL LEVEL: {skill_level or "Not specified"}
CADENCE: {cadence}

Address the user's specific concerns and create an improved roadmap."""

    try:
        response = await client.aio.models.generate_content(
            model="gemini-2.5-pro",  # Use pro model for regeneration
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=ROADMAP_SYSTEM_PROMPT,
                temperature=1,
                response_mime_type="application/json",
            ),
        )

        result = json.loads(response.text)
        return result

    except Exception as e:
        return _generate_fallback_roadmap(goal_statement, category, cadence)
