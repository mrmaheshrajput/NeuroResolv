import json
import os
from typing import Optional
from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from app.config import get_settings
from app.services import query_collection
from app.observability import track_llm_call

settings = get_settings()

os.environ["GOOGLE_API_KEY"] = settings.google_api_key


def create_syllabus_agent() -> Agent:
    return Agent(
        name="syllabus_generator",
        model="gemini-flash-lite-latest",
        description="Generates personalized learning syllabi based on user goals and uploaded content",
        instruction="""You are an expert curriculum designer and learning specialist. Your task is to create 
a personalized, structured learning syllabus based on the user's learning goal and available content.

When generating a syllabus:
1. Analyze the learning goal and time commitment
2. Review the available content from the knowledge base
3. Design a progressive curriculum that builds concepts incrementally
4. Ensure each day focuses on digestible, micro-learning chunks
5. Include specific concepts to be covered each day
6. Estimate realistic time for each session

Output Format (JSON):
{
    "title": "Syllabus title",
    "total_days": number,
    "days": [
        {
            "day": 1,
            "title": "Day title",
            "description": "What will be learned",
            "concepts": ["concept1", "concept2"],
            "estimated_minutes": 30
        }
    ],
    "learning_objectives": ["objective1", "objective2"],
    "prerequisites": []
}

Make the syllabus engaging, progressive, and achievable within the daily time limit.""",
        tools=[retrieve_content_tool],
    )


def retrieve_content_tool(query: str, resolution_id: int) -> dict:
    """Retrieves relevant content from the user's uploaded learning materials.
    
    Args:
        query: Search query to find relevant content
        resolution_id: The resolution ID to search within
        
    Returns:
        dict: Retrieved content chunks with metadata
    """
    import asyncio
    
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    try:
        results = loop.run_until_complete(query_collection(resolution_id, query, n_results=5))
        return {
            "status": "success",
            "documents": results.get("documents", [[]]),
            "metadatas": results.get("metadatas", [[]]),
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


@track_llm_call("generate_syllabus")
async def generate_syllabus(
    goal_statement: str,
    resolution_id: int,
    duration_days: int = 30,
    daily_minutes: int = 30,
    content_summary: Optional[str] = None,
) -> dict:
    agent = create_syllabus_agent()
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
    
    prompt = f"""Create a {duration_days}-day learning syllabus for the following goal:

Goal: {goal_statement}

Daily Time Commitment: {daily_minutes} minutes

{"Content Available: " + content_summary if content_summary else "Note: User will upload learning materials. Design a general structure that can be adapted."}

Resolution ID for content retrieval: {resolution_id}

Please generate a comprehensive, day-by-day syllabus that will help the user achieve their learning goal.
Return the syllabus as a valid JSON object."""

    result = None
    async for event in runner.run_async(
        user_id=f"resolution_{resolution_id}",
        session_id=session.id,
        new_message=types.Content(
            role="user",
            parts=[types.Part(text=prompt)]
        ),
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
    
    return _generate_fallback_syllabus(goal_statement, duration_days, daily_minutes)


def _generate_fallback_syllabus(goal: str, days: int, minutes: int) -> dict:
    daily_items = []
    for i in range(1, days + 1):
        phase = "Foundation" if i <= days // 3 else ("Building" if i <= 2 * days // 3 else "Mastery")
        daily_items.append({
            "day": i,
            "title": f"Day {i}: {phase} Phase",
            "description": f"Continue learning journey - {phase.lower()} concepts",
            "concepts": [f"concept_{i}_a", f"concept_{i}_b"],
            "estimated_minutes": minutes,
        })
    
    return {
        "title": f"Learning Journey: {goal[:50]}...",
        "total_days": days,
        "days": daily_items,
        "learning_objectives": ["Understand core concepts", "Apply knowledge practically"],
        "prerequisites": [],
    }
