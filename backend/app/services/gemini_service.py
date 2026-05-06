import json
from functools import lru_cache
from typing import Any

from google import genai
from google.genai import types

from app.config import GEMINI_API_KEY, GEMINI_MODEL, LLM_PROVIDER
from app.services.local_llm_service import LocalLLMServiceError, generate_json_local


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


def _generate_json_gemini(prompt: str, response_schema: dict) -> dict:
    response = get_gemini_client().models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=response_schema,
        ),
    )
    result = _extract_json(response)
    result.setdefault("attempts", 1)
    result.setdefault("fallback_used", False)
    return result


def _generate_json_local(prompt: str, response_schema: dict) -> dict:
    result = generate_json_local(prompt, response_schema)
    result.setdefault("attempts", 1)
    result["fallback_used"] = True
    return result


def generate_json(prompt: str, response_schema: dict) -> dict:
    if not prompt.strip():
        raise GeminiServiceError("Prompt cannot be empty")

    provider = LLM_PROVIDER if LLM_PROVIDER in {"gemini", "local", "auto"} else "auto"
    print(f"[gemini_service] provider={provider}")

    if provider == "local":
        print("[gemini_service] using local provider")
        try:
            return _generate_json_local(prompt, response_schema)
        except LocalLLMServiceError as exc:
            raise GeminiServiceError(
                f"Local provider failed: {type(exc).__name__}: {exc}"
            ) from exc

    if provider == "gemini":
        try:
            return _generate_json_gemini(prompt, response_schema)
        except Exception as exc:
            print(f"[gemini_service] error={type(exc).__name__}: {exc}")
            raise GeminiServiceError(
                f"Gemini request failed: {type(exc).__name__}: {exc}"
            ) from exc

    try:
        return _generate_json_gemini(prompt, response_schema)
    except Exception as exc:
        print(f"[gemini_service] error={type(exc).__name__}: {exc}")
        gemini_error = exc

    print("[gemini_service] falling back to local provider")
    try:
        return _generate_json_local(prompt, response_schema)
    except LocalLLMServiceError as exc:
        raise GeminiServiceError(
            "Gemini request failed and local LLM fallback failed: "
            f"gemini={type(gemini_error).__name__}: {gemini_error}; "
            f"local={type(exc).__name__}: {exc}"
        ) from exc
