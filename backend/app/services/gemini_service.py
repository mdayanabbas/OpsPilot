import json
from functools import lru_cache
from typing import Any

from google import genai
from google.genai import types

from app.config import GEMINI_API_KEY, GEMINI_MODEL


class GeminiServiceError(RuntimeError):
    """Raised when Gemini cannot return a valid structured response."""


@lru_cache(maxsize=1)
def get_gemini_client() -> genai.Client:
    if not GEMINI_API_KEY:
        raise GeminiServiceError("GEMINI_API_KEY is not configured")

    return genai.Client(api_key=GEMINI_API_KEY)


def _extract_json(response: Any) -> dict:
    parsed = getattr(response, "parsed", None)
    if isinstance(parsed, dict):
        return parsed

    text = getattr(response, "text", None)
    if not text:
        raise GeminiServiceError("Gemini returned an empty response")

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise GeminiServiceError("Gemini returned invalid JSON") from exc

    if not isinstance(data, dict):
        raise GeminiServiceError("Gemini JSON response must be an object")

    return data


def generate_json(prompt: str, response_schema: dict) -> dict:
    if not prompt.strip():
        raise GeminiServiceError("Prompt cannot be empty")

    try:
        response = get_gemini_client().models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=response_schema,
            ),
        )
    except Exception as exc:
        print(f"[gemini_service] error={type(exc).__name__}: {exc}")
        raise GeminiServiceError(f"Gemini request failed: {type(exc).__name__}: {exc}") from exc

    return _extract_json(response)
