import json
from functools import lru_cache
from typing import Any

from google import genai
from google.genai import types

from app.config import GEMINI_API_KEY, GEMINI_MODEL, LLM_PROVIDER
from app.services.local_llm_service import LocalLLMServiceError, generate_json_local


class GeminiServiceError(RuntimeError):
    """Raised when Gemini cannot return a valid structured response."""


def _strip_code_fence(text: str) -> str:
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped

    lines = stripped.splitlines()
    if lines and lines[0].strip().startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()


def _first_json_object(text: str) -> str:
    start_positions = [index for index, char in enumerate(text) if char == "{"]
    for start in start_positions:
        depth = 0
        in_string = False
        escape = False

        for index in range(start, len(text)):
            char = text[index]

            if in_string:
                if escape:
                    escape = False
                elif char == "\\":
                    escape = True
                elif char == '"':
                    in_string = False
                continue

            if char == '"':
                in_string = True
            elif char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    candidate = text[start : index + 1]
                    try:
                        json.loads(candidate)
                    except json.JSONDecodeError:
                        break
                    return candidate

    raise GeminiServiceError("No valid JSON object found in Gemini response")


def _parse_json_object(text: str) -> dict:
    stripped = _strip_code_fence(text)

    try:
        data = json.loads(stripped)
    except json.JSONDecodeError:
        try:
            data = json.loads(_first_json_object(stripped))
        except json.JSONDecodeError as exc:
            raise GeminiServiceError("Gemini returned invalid JSON") from exc

    if isinstance(data, str):
        return _parse_json_object(data)

    if not isinstance(data, dict):
        raise GeminiServiceError("Gemini JSON response must be an object")

    return data


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

    return _parse_json_object(text)


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
    result.setdefault("provider", "gemini")
    return result


def _generate_json_local(prompt: str, response_schema: dict, *, fallback_used: bool) -> dict:
    result = generate_json_local(prompt, response_schema)
    result.setdefault("attempts", 1)
    result["fallback_used"] = fallback_used
    result["provider"] = "fallback" if fallback_used else "local"
    return result


def generate_json(prompt: str, response_schema: dict) -> dict:
    if not prompt.strip():
        raise GeminiServiceError("Prompt cannot be empty")

    provider = LLM_PROVIDER if LLM_PROVIDER in {"gemini", "local", "auto"} else "local"
    print(f"[gemini_service] provider={provider}")

    if provider == "local":
        print("[LLM_service] using local provider")
        try:
            return _generate_json_local(prompt, response_schema, fallback_used=False)
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
        return _generate_json_local(prompt, response_schema, fallback_used=True)
    except LocalLLMServiceError as exc:
        raise GeminiServiceError(
            "Gemini request failed and local LLM fallback failed: "
            f"gemini={type(gemini_error).__name__}: {gemini_error}; "
            f"local={type(exc).__name__}: {exc}"
        ) from exc
