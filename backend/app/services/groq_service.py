import json
from functools import lru_cache

from openai import OpenAI

from app.config import GROQ_API_KEY, GROQ_BASE_URL, GROQ_MODEL, LLM_PROVIDER
from app.services.local_llm_service import LocalLLMServiceError, generate_json_local


class GroqServiceError(RuntimeError):
    """Raised when Groq cannot return a valid structured response."""


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
    decoder = json.JSONDecoder()
    for index, character in enumerate(text):
        if character != "{":
            continue
        try:
            parsed, end = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return text[index : index + end]
    raise GroqServiceError("No valid JSON object found in Groq response")


def _parse_json_object(text: str) -> dict:
    stripped = _strip_code_fence(text)
    try:
        data = json.loads(stripped)
    except json.JSONDecodeError:
        data = json.loads(_first_json_object(stripped))
    if isinstance(data, str):
        return _parse_json_object(data)
    if not isinstance(data, dict):
        raise GroqServiceError("Groq JSON response must be an object")
    if "type" in data and "properties" in data:
        raise GroqServiceError("Groq returned the schema instead of an answer")
    return data


@lru_cache(maxsize=1)
def get_groq_client() -> OpenAI:
    if not GROQ_API_KEY:
        raise GroqServiceError("GROQ_API_KEY is not configured")
    return OpenAI(api_key=GROQ_API_KEY, base_url=GROQ_BASE_URL)


def _generate_json_groq(prompt: str, response_schema: dict) -> dict:
    response = get_groq_client().chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a strict JSON generator. Return only one final JSON "
                    "object with no markdown, explanation, or schema metadata."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"{prompt}\n\nUse this JSON schema only as output constraints. "
                    "Do not echo the schema. Return only the populated JSON object:\n"
                    f"{json.dumps(response_schema, separators=(',', ':'))}"
                ),
            },
        ],
        response_format={"type": "json_object"},
        temperature=0.1,
    )
    content = response.choices[0].message.content or ""
    if not content.strip():
        raise GroqServiceError("Groq returned an empty response")
    result = _parse_json_object(content)
    result.setdefault("attempts", 1)
    result.setdefault("fallback_used", False)
    result.setdefault("provider", "groq")
    return result


def _generate_json_local(prompt: str, response_schema: dict, *, fallback_used: bool) -> dict:
    result = generate_json_local(prompt, response_schema)
    result.setdefault("attempts", 1)
    result["fallback_used"] = fallback_used
    result["provider"] = "fallback" if fallback_used else "local"
    return result


def generate_json(prompt: str, response_schema: dict) -> dict:
    if not prompt.strip():
        raise GroqServiceError("Prompt cannot be empty")

    provider = LLM_PROVIDER if LLM_PROVIDER in {"groq", "local", "auto"} else "groq"
    print(f"[groq_service] provider={provider}")

    if provider == "local":
        try:
            return _generate_json_local(prompt, response_schema, fallback_used=False)
        except LocalLLMServiceError as exc:
            raise GroqServiceError(
                f"Local provider failed: {type(exc).__name__}: {exc}"
            ) from exc

    if provider == "groq":
        try:
            return _generate_json_groq(prompt, response_schema)
        except Exception as exc:
            print(f"[groq_service] error={type(exc).__name__}: {exc}")
            if isinstance(exc, GroqServiceError):
                raise
            raise GroqServiceError(
                f"Groq request failed: {type(exc).__name__}: {exc}"
            ) from exc

    try:
        return _generate_json_groq(prompt, response_schema)
    except Exception as exc:
        print(f"[groq_service] error={type(exc).__name__}: {exc}")
        groq_error = exc

    print("[groq_service] falling back to local provider")
    try:
        return _generate_json_local(prompt, response_schema, fallback_used=True)
    except LocalLLMServiceError as exc:
        raise GroqServiceError(
            "Groq request failed and local LLM fallback failed: "
            f"groq={type(groq_error).__name__}: {groq_error}; "
            f"local={type(exc).__name__}: {exc}"
        ) from exc
