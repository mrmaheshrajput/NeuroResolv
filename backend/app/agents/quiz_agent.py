import json
import os
from typing import Optional

from app.config import get_settings
from app.observability import track_llm_call
from app.services import query_collection
from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

settings = get_settings()

os.environ["GOOGLE_API_KEY"] = settings.google_api_key


def create_quiz_agent() -> Agent:
    return Agent(
        name="quiz_generator",
        model="gemini-flash-lite-latest",
        description="Generates active recall quizzes to test comprehension of learning content",
        instruction="""You are an expert educational assessor specializing in active recall techniques.
Your task is to generate effective quiz questions that test genuine understanding, not just memorization.

Guidelines for quiz generation:
1. Focus on key concepts and their applications
2. Mix question types: multiple choice, true/false, and short answer
3. Ensure questions test understanding, not just recall
4. Include varying difficulty levels
5. Tag each question with the concept it tests
6. Make wrong options plausible but clearly incorrect

Output Format (JSON):
{
    "questions": [
        {
            "type": "multiple_choice",
            "question": "Question text",
            "options": ["A", "B", "C", "D"],
            "correct_answer": "B",
            "concept": "concept_name",
            "difficulty": "medium",
            "explanation": "Why this answer is correct"
        },
        {
            "type": "true_false",
            "question": "Statement to evaluate",
            "correct_answer": "true",
            "concept": "concept_name",
            "difficulty": "easy",
            "explanation": "Why this is true/false"
        },
        {
            "type": "short_answer",
            "question": "Open-ended question",
            "correct_answer": "Expected key points",
            "concept": "concept_name",
            "difficulty": "hard",
            "explanation": "What a good answer should include"
        }
    ]
}

Generate 5-7 diverse questions that effectively test the day's learning material.""",
        tools=[],
    )


@track_llm_call("generate_quiz")
async def generate_quiz(
    session_content: str,
    session_title: str,
    concepts: list[str],
    user_performance_history: Optional[dict] = None,
) -> dict:
    agent = create_quiz_agent()
    session_service = InMemorySessionService()

    runner = Runner(
        agent=agent,
        app_name="neuroresolv",
        session_service=session_service,
    )

    session = await session_service.create_session(
        app_name="neuroresolv",
        user_id="quiz_generator",
    )

    difficulty_note = ""
    if user_performance_history:
        avg_score = user_performance_history.get("average_score", 70)
        if avg_score > 85:
            difficulty_note = (
                "User has been performing well. Include more challenging questions."
            )
        elif avg_score < 60:
            difficulty_note = (
                "User has been struggling. Focus on foundational questions."
            )

    prompt = f"""Generate a quiz for the following learning session:

Session Title: {session_title}

Content Covered:
{session_content[:3000]}

Key Concepts to Test: {', '.join(concepts)}

{difficulty_note}

Create 5-7 diverse questions that test understanding of the material.
Return the quiz as a valid JSON object with the questions array."""

    result = None
    async for event in runner.run_async(
        user_id="quiz_generator",
        session_id=session.id,
        new_message=types.Content(role="user", parts=[types.Part(text=prompt)]),
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

    return _generate_fallback_quiz(concepts)


def _generate_fallback_quiz(concepts: list[str]) -> dict:
    questions = []

    for i, concept in enumerate(concepts[:5]):
        questions.append(
            {
                "type": "multiple_choice",
                "question": f"Which of the following best describes {concept}?",
                "options": [
                    f"A common application of {concept}",
                    f"The core principle of {concept}",
                    f"An unrelated concept",
                    f"A prerequisite for {concept}",
                ],
                "correct_answer": f"The core principle of {concept}",
                "concept": concept,
                "difficulty": "medium",
                "explanation": f"This tests understanding of {concept}.",
            }
        )

    if len(concepts) > 0:
        questions.append(
            {
                "type": "true_false",
                "question": f"{concepts[0]} is a fundamental concept in this learning path.",
                "correct_answer": "true",
                "concept": concepts[0],
                "difficulty": "easy",
                "explanation": f"{concepts[0]} is indeed a core concept covered today.",
            }
        )

    return {"questions": questions}


@track_llm_call("grade_answer")
async def grade_short_answer(
    question: str,
    expected_answer: str,
    user_answer: str,
    concept: str,
) -> dict:
    agent = Agent(
        name="answer_grader",
        model="gemini-flash-lite-latest",
        description="Grades short answer responses",
        instruction="""You are an expert grader. Evaluate the user's answer against the expected answer.
Be fair but rigorous. Look for key concepts and understanding, not exact wording.

Output Format (JSON):
{
    "is_correct": true/false,
    "score": 0.0-1.0,
    "feedback": "Explanation of what was good/missing",
    "key_points_hit": ["point1", "point2"],
    "key_points_missed": ["point3"]
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
        user_id="grader",
    )

    prompt = f"""Grade this answer:

Question: {question}
Expected Answer: {expected_answer}
User's Answer: {user_answer}
Concept Being Tested: {concept}

Evaluate and return a JSON grade."""

    result = None
    async for event in runner.run_async(
        user_id="grader",
        session_id=session.id,
        new_message=types.Content(role="user", parts=[types.Part(text=prompt)]),
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
        "is_correct": False,
        "score": 0.5,
        "feedback": "Unable to grade automatically. Answer noted for review.",
        "key_points_hit": [],
        "key_points_missed": [],
    }
