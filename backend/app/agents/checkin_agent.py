import json
from app.config import get_settings
from app.observability import track_llm_call
from google import genai
from google.genai import types

settings = get_settings()
client = genai.Client(api_key=settings.google_api_key)

CHECKIN_SYSTEM_PROMPT = """You are an encouraging accountability partner.
Your role is to analyze a user's check-in (text, image, video, or audio) for their habit/goal.

You need to output a JSON object with two fields:
1. "description": A factual summary of what is seen/heard or claimed. (Max 2 sentences).
2. "reflection": A warm, encouraging, and specific response to the user.
   - Acknowledge their effort.
   - If they shared media (image, video, audio), mention specific details to prove you analyzed it.
   - Connect it to their progress/streak if mentioned.
   - Be transformational, not transactional. Focus on the journey.

Return JSON:
{
  "description": "User is reading 'Atomic Habits', page 45.",
  "reflection": "That's fantastic! Reading 'Atomic Habits' is a game changer. I love that you're diving deep into the concepts."
}"""


@track_llm_call("analyze_checkin")
async def analyze_checkin(
    input_type: str,
    content: str | bytes,
    mime_type: str | None,
    goal_context: str,
    recent_history: str,
) -> dict:
    prompt = f"""Analyze this check-in:

GOAL: {goal_context}
RECENT HISTORY: {recent_history}

INPUT TYPE: {input_type}
"""

    parts = [prompt]

    if input_type != "text" and mime_type:
        # content is bytes or base64
        parts.append(types.Part.from_bytes(data=content, mime_type=mime_type))
    elif input_type == "text":
        parts.append(f"USER TEXT: {content}")

    try:
        response = await client.aio.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=parts,
            config=types.GenerateContentConfig(
                system_instruction=CHECKIN_SYSTEM_PROMPT,
                temperature=0.7,
                response_mime_type="application/json",
            ),
        )

        return json.loads(response.text)

    except Exception as e:
        print(f"Error in analyze_checkin: {e}")
        return {
            "description": "Check-in logged.",
            "reflection": "Great job checking in! Keep up the momentum.",
        }
