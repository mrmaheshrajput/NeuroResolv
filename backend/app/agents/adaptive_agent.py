import json
import os
from typing import Optional
from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

from app.config import get_settings
from app.services import query_collection
from app.observability import track_llm_call, log_adaptive_decision

settings = get_settings()

os.environ["GOOGLE_API_KEY"] = settings.google_api_key


def create_adaptive_agent() -> Agent:
    return Agent(
        name="adaptive_tutor",
        model="gemini-2.0-flash",
        description="Adapts learning paths based on quiz performance and concept mastery",
        instruction="""You are an expert adaptive learning specialist. Your role is to analyze 
student performance and adapt their learning path to reinforce weak areas.

When a student fails a quiz or shows weakness in specific concepts:
1. Identify the exact concepts that need reinforcement
2. Design targeted review materials
3. Suggest modifications to the upcoming sessions
4. Create a reinforcement plan that integrates with the existing syllabus

Key Principles:
- Don't just repeat content; approach weak concepts from different angles
- Build connections between weak and strong concepts
- Provide encouragement while being honest about areas needing work
- Keep the learning engaging, not punishment-like

Output Format (JSON):
{
    "adaptation_type": "reinforcement|review|restructure",
    "weak_concepts": ["concept1", "concept2"],
    "reinforcement_content": {
        "title": "Review Session Title",
        "description": "What this review covers",
        "approach": "Different angle to teach the concept",
        "activities": ["activity1", "activity2"],
        "estimated_minutes": 20
    },
    "syllabus_modifications": [
        {
            "day": 5,
            "modification": "Add 10 minutes for concept review",
            "reason": "Student showed weakness in prerequisite"
        }
    ],
    "encouragement_message": "Personalized encouraging message",
    "study_tips": ["tip1", "tip2"]
}""",
        tools=[retrieve_weak_concept_content],
    )


def retrieve_weak_concept_content(concept: str, resolution_id: int) -> dict:
    """Retrieves additional content related to a weak concept.
    
    Args:
        concept: The concept the student is struggling with
        resolution_id: The resolution ID to search within
        
    Returns:
        dict: Related content that could help reinforce the concept
    """
    import asyncio
    
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    try:
        results = loop.run_until_complete(
            query_collection(resolution_id, f"explain {concept} fundamentals basics", n_results=3)
        )
        return {
            "status": "success",
            "documents": results.get("documents", [[]]),
            "metadatas": results.get("metadatas", [[]]),
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


@track_llm_call("adapt_learning_path")
async def adapt_learning_path(
    resolution_id: int,
    quiz_score: float,
    weak_concepts: list[str],
    strong_concepts: list[str],
    current_day: int,
    remaining_days: int,
    current_syllabus: dict,
) -> dict:
    agent = create_adaptive_agent()
    session_service = InMemorySessionService()
    
    runner = Runner(
        agent=agent,
        app_name="neuroresolv",
        session_service=session_service,
    )
    
    session = await session_service.create_session(
        app_name="neuroresolv",
        user_id=f"resolution_{resolution_id}",
    )
    
    severity = "minor" if quiz_score >= 60 else ("moderate" if quiz_score >= 40 else "significant")
    
    prompt = f"""Analyze this student's performance and create an adaptation plan:

Quiz Score: {quiz_score}% ({severity} intervention needed)
Current Day: {current_day} of {current_day + remaining_days} total

Weak Concepts (need reinforcement):
{json.dumps(weak_concepts, indent=2)}

Strong Concepts (understood well):
{json.dumps(strong_concepts, indent=2)}

Upcoming Syllabus Days:
{json.dumps(current_syllabus.get('days', [])[current_day:current_day+5], indent=2)}

Resolution ID for content retrieval: {resolution_id}

Create an adaptive learning plan that:
1. Reinforces weak concepts through different approaches
2. Suggests how to modify upcoming sessions
3. Provides encouragement and actionable study tips

Return a valid JSON adaptation plan."""

    result = None
    async for event in runner.run_async(
        user_id=f"resolution_{resolution_id}",
        session_id=session.id,
        new_message=prompt,
    ):
        if hasattr(event, "content") and event.content:
            if hasattr(event.content, "parts"):
                for part in event.content.parts:
                    if hasattr(part, "text"):
                        result = part.text
    
    adaptation = None
    if result:
        try:
            json_start = result.find("{")
            json_end = result.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                adaptation = json.loads(result[json_start:json_end])
        except json.JSONDecodeError:
            pass
    
    if not adaptation:
        adaptation = _generate_fallback_adaptation(weak_concepts, quiz_score)
    
    await log_adaptive_decision(
        resolution_id=resolution_id,
        weak_concepts=weak_concepts,
        adaptation_type=adaptation.get("adaptation_type", "reinforcement"),
        original_plan={"current_day": current_day},
        adapted_plan=adaptation,
    )
    
    return adaptation


def _generate_fallback_adaptation(weak_concepts: list[str], score: float) -> dict:
    return {
        "adaptation_type": "reinforcement",
        "weak_concepts": weak_concepts,
        "reinforcement_content": {
            "title": "Concept Review Session",
            "description": f"Focused review of: {', '.join(weak_concepts)}",
            "approach": "Breaking down concepts into smaller parts with examples",
            "activities": [
                "Re-read the original material with focus on weak areas",
                "Create your own examples for each concept",
                "Explain the concept in your own words",
            ],
            "estimated_minutes": 20,
        },
        "syllabus_modifications": [],
        "encouragement_message": "Every expert was once a beginner. Let's reinforce these concepts together!",
        "study_tips": [
            "Try teaching the concept to someone else",
            "Create flashcards for quick review",
            "Look for real-world examples of these concepts",
        ],
    }


@track_llm_call("generate_reinforcement_content")
async def generate_reinforcement_content(
    resolution_id: int,
    weak_concepts: list[str],
    previous_explanations: list[str],
) -> dict:
    agent = Agent(
        name="content_reinforcer",
        model="gemini-2.0-flash",
        description="Creates alternative explanations for difficult concepts",
        instruction="""Create new, alternative explanations for concepts the student is struggling with.
Use different analogies, examples, and approaches than previously used.
Focus on building understanding from first principles.

Output Format (JSON):
{
    "reinforcement_materials": [
        {
            "concept": "concept_name",
            "alternative_explanation": "New way to explain",
            "analogy": "Real-world analogy",
            "example": "Concrete example",
            "practice_exercise": "Simple exercise to test understanding"
        }
    ]
}""",
        tools=[],
    )
    
    session_service = InMemorySessionService()
    runner = Runner(
        agent=agent,
        app_name="neuroresolv",
        session_service=session_service,
    )
    
    session = await session_service.create_session(
        app_name="neuroresolv",
        user_id=f"resolution_{resolution_id}",
    )
    
    prompt = f"""Create reinforcement materials for these concepts:

Concepts needing reinforcement:
{json.dumps(weak_concepts, indent=2)}

Previous explanations that didn't work well:
{json.dumps(previous_explanations[:500] if previous_explanations else ["No previous explanations available"], indent=2)}

Generate new, alternative ways to teach these concepts.
Return a valid JSON object with reinforcement materials."""

    result = None
    async for event in runner.run_async(
        user_id=f"resolution_{resolution_id}",
        session_id=session.id,
        new_message=prompt,
    ):
        if hasattr(event, "content") and event.content:
            if hasattr(event.content, "parts"):
                for part in event.content.parts:
                    if hasattr(part, "text"):
                        result = part.text
    
    if result:
        try:
            json_start = result.find("{")
            json_end = result.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                return json.loads(result[json_start:json_end])
        except json.JSONDecodeError:
            pass
    
    return {
        "reinforcement_materials": [
            {
                "concept": concept,
                "alternative_explanation": f"Let's think about {concept} differently...",
                "analogy": f"Think of {concept} like...",
                "example": f"A practical example of {concept} is...",
                "practice_exercise": f"Try explaining {concept} in your own words.",
            }
            for concept in weak_concepts
        ]
    }
