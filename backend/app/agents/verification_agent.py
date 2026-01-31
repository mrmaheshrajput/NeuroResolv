import json
from google import genai
from google.genai import types

from app.config import get_settings
from app.observability import track_llm_call


settings = get_settings()
client = genai.Client(api_key=settings.google_api_key)


VERIFICATION_SYSTEM_PROMPT = """You are an expert learning verifier who creates contextual quiz questions.

Your task is to generate verification questions based on what the user claims to have studied today.
You must validate their understanding, not just their completion.

Rules:
1. Generate 3-5 questions that test genuine understanding
2. Questions should be based on the topic/content the user mentions
3. Include a mix of:
   - Concept explanation (explain X in your own words)
   - Application (how would you use X in situation Y)
   - Comparison (what's the difference between X and Y)
   - Recall (what are the key points of X)
4. If you're unsure about the specific content, fall back to open-ended "teach-back" questions
5. Always include at least one "teach-back" question as the final question

Return JSON:
{
  "questions": [
    {
      "id": 1,
      "question_type": "concept|application|comparison|recall|teach_back",
      "question_text": "The question",
      "options": null,
      "concept": "What concept this tests"
    }
  ],
  "search_context": "Brief context about what was researched to generate these questions"
}"""


@track_llm_call("context_aware_quiz")
async def generate_verification_quiz(
    progress_content: str,
    source_reference: str | None,
    goal_context: str,
    previous_concepts: list[str] | None = None,
) -> dict:
    search_context = None

    if source_reference:
        search_context = await _search_for_context(progress_content, source_reference)

    prompt = f"""Generate verification questions for this learning session:

USER'S PROGRESS LOG: "{progress_content}"

SOURCE REFERENCED: {source_reference or "Not specified"}

GOAL CONTEXT: {goal_context}

{f"ADDITIONAL CONTEXT FROM SEARCH: {search_context}" if search_context else ""}

{f"CONCEPTS PREVIOUSLY COVERED: {', '.join(previous_concepts)}" if previous_concepts else ""}

Generate questions that verify the user actually learned and understood what they claim.
If you can't determine specific content, use open-ended teach-back questions."""

    try:
        response = await client.aio.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=VERIFICATION_SYSTEM_PROMPT,
                temperature=0.6,
                response_mime_type="application/json",
            ),
        )

        result = json.loads(response.text)

        for i, q in enumerate(result.get("questions", [])):
            q["id"] = i + 1

        return result

    except Exception as e:
        return _generate_fallback_quiz(progress_content)


async def _search_for_context(content: str, source: str) -> str | None:
    search_query = f"{source} {content[:100]} key concepts summary"

    try:
        response = await client.aio.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=search_query,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
                temperature=0.3,
            ),
        )

        if response.candidates and response.candidates[0].grounding_metadata:
            chunks = response.candidates[0].grounding_metadata.grounding_chunks
            if chunks:
                context_parts = []
                for chunk in chunks[:3]:
                    if hasattr(chunk, "web") and chunk.web:
                        context_parts.append(chunk.web.title or "")
                return " | ".join(context_parts)

        return response.text[:500] if response.text else None

    except Exception:
        return None


def _generate_fallback_quiz(content: str) -> dict:
    return {
        "questions": [
            {
                "id": 1,
                "question_type": "recall",
                "question_text": "What were the main points or concepts you learned today?",
                "options": None,
                "concept": "general_recall",
            },
            {
                "id": 2,
                "question_type": "application",
                "question_text": "How could you apply what you learned today in a real situation?",
                "options": None,
                "concept": "practical_application",
            },
            {
                "id": 3,
                "question_type": "teach_back",
                "question_text": "Explain what you learned today as if teaching someone who knows nothing about the topic.",
                "options": None,
                "concept": "teach_back_validation",
            },
        ],
        "search_context": "Fallback questions - no specific context available",
    }


GRADING_SYSTEM_PROMPT = """You are an expert learning evaluator who grades open-ended responses.

Evaluate each answer for:
1. Accuracy - Is the information correct?
2. Depth - Does it show genuine understanding beyond surface level?
3. Clarity - Is it clearly explained?
4. Completeness - Does it cover the key points?

Return JSON:
{
  "evaluations": [
    {
      "question_id": 1,
      "score": 0.0-1.0,
      "is_correct": true/false,
      "feedback": "Specific feedback",
      "key_points_identified": ["point1", "point2"],
      "missed_concepts": ["concept1"]
    }
  ],
  "overall_score": 0.0-1.0,
  "passed": true/false,
  "summary_feedback": "Overall assessment",
  "concepts_to_reinforce": ["concept1", "concept2"]
}"""


@track_llm_call("quiz_grading")
async def grade_verification_quiz(
    questions: list[dict],
    answers: list[dict],
    context: str,
) -> dict:
    qa_pairs = []
    for q in questions:
        answer = next((a for a in answers if a.get("question_id") == q.get("id")), None)
        qa_pairs.append(
            {
                "question": q.get("question_text"),
                "type": q.get("question_type"),
                "concept": q.get("concept"),
                "answer": answer.get("answer") if answer else "No answer provided",
            }
        )

    prompt = f"""Grade these learning verification responses:

CONTEXT: {context}

QUESTIONS AND ANSWERS:
{json.dumps(qa_pairs, indent=2)}

Evaluate each answer and provide an overall assessment.
Pass threshold is 60% overall score."""

    try:
        response = await client.aio.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=GRADING_SYSTEM_PROMPT,
                temperature=0.3,
                response_mime_type="application/json",
            ),
        )

        return json.loads(response.text)

    except Exception:
        return {
            "evaluations": [],
            "overall_score": 0.5,
            "passed": True,
            "summary_feedback": "Unable to provide detailed feedback. Marked as verified.",
            "concepts_to_reinforce": [],
        }
