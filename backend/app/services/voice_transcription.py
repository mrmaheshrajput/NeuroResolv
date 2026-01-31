import base64
import os
import tempfile

from app.config import get_settings
from openai import AsyncOpenAI

settings = get_settings()


async def transcribe_voice_note(audio_base64: str) -> dict:
    """Transcribe a voice note using OpenAI Whisper."""
    audio_bytes = base64.b64decode(audio_base64)

    with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as temp_file:
        temp_file.write(audio_bytes)
        temp_path = temp_file.name

    try:
        client = AsyncOpenAI(api_key=settings.openai_api_key)

        with open(temp_path, "rb") as audio_file:
            transcript = await client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="text",
            )

        return {
            "text": transcript,
            "duration_seconds": None,
        }

    except Exception as e:
        raise ValueError(f"Transcription failed: {str(e)}")

    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)
