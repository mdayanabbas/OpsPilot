import json
import re
from typing import Any, Dict

from openai import OpenAI

from app.config import (
    LOCAL_LLM_API_KEY,
    LOCAL_LLM_BASE_URL,
    LOCAL_LLM_ENABLED,
    LOCAL_LLM_MODEL,
)


class LocalLLMServiceError(Exception):
    pass


def _extract_json_object(text: str) -> Dict[str, Any]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise LocalLLMServiceError("No JSON object found in local LLM response.")

    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        raise LocalLLMServiceError(f"Invalid JSON from local LLM: {exc}") from exc


def generate_json_local(prompt: str, response_schema: Dict[str, Any]) -> Dict[str, Any]:
    if not LOCAL_LLM_ENABLED:
        raise LocalLLMServiceError("Local LLM fallback is disabled.")

    client = OpenAI(
        base_url=LOCAL_LLM_BASE_URL,
        api_key=LOCAL_LLM_API_KEY,
    )

    system_prompt = (
        "You are a strict JSON generator. "
        "Return only the final JSON object answer. "
        "Do not return JSON schema. "
        "Do not include type, properties, or required as schema metadata. "
        "Do not include markdown, explanations, or code fences."
    )

    try:
        response = client.chat.completions.create(
            model=LOCAL_LLM_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": (
                        f"{prompt}\n\n"
                        "Do NOT return JSON schema.\n"
                        "Do NOT include type/properties/required.\n"
                        "Return ONLY the final JSON object.\n\n"
                        "Example of the expected answer format:\n"
                        "{\n"
                        '  "workflow_type": "customer_feedback_triage",\n'
                        '  "confidence": 0.82,\n'
                        '  "reason": "The input describes customer feedback that needs triage.",\n'
                        '  "requires_clarification": false\n'
                        "}\n\n"
                        "Use this schema only as constraints for the final answer. "
                        "Do not echo it:\n"
                        f"{json.dumps(response_schema, indent=2)}"
                    ),
                },
            ],
            temperature=0.1,
        )

        content = response.choices[0].message.content or ""
        parsed = _extract_json_object(content)
        if "type" in parsed and "properties" in parsed:
            raise LocalLLMServiceError(
                "Local LLM returned schema instead of answer."
            )

        return parsed

    except LocalLLMServiceError:
        raise
    except Exception as exc:
        print(f"[local_llm_service] error={type(exc).__name__}: {exc}")
        raise LocalLLMServiceError(
            f"Local LLM request failed: {type(exc).__name__}: {exc}"
        ) from exc
