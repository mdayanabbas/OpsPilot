from app.services.gemini_service import generate_json
from app.tools.retry_controller import retry_with_fallback


INTENT_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "workflow_type": {"type": "string"},
        "confidence": {"type": "number"},
        "reason": {"type": "string"},
        "requires_clarification": {"type": "boolean"},
    },
    "required": [
        "workflow_type",
        "confidence",
        "reason",
        "requires_clarification",
    ],
}


def _fallback_intent(
    reason: str,
    confidence: float = 0.55,
) -> dict:
    return {
        "workflow_type": "customer_feedback_triage",
        "confidence": confidence,
        "reason": reason,
        "requires_clarification": True,
    }


def _normalize_intent(raw_intent: dict) -> dict:
    workflow_type = raw_intent.get("workflow_type")
    if workflow_type != "customer_feedback_triage":
        workflow_type = "customer_feedback_triage"

    try:
        confidence = float(raw_intent.get("confidence", 0.0))
    except (TypeError, ValueError):
        confidence = 0.0
    confidence = max(0.0, min(confidence, 1.0))

    reason = raw_intent.get("reason")
    if not isinstance(reason, str) or not reason.strip():
        reason = "Classified as customer feedback triage."

    requires_clarification = raw_intent.get("requires_clarification", False)
    if not isinstance(requires_clarification, bool):
        requires_clarification = bool(requires_clarification)

    return {
        "workflow_type": workflow_type,
        "confidence": confidence,
        "reason": reason,
        "requires_clarification": requires_clarification,
    }


def detect_workflow_intent(input_text: str) -> dict:
    if not isinstance(input_text, str) or not input_text.strip():
        intent = _fallback_intent("Input text is empty or invalid.")
        intent["attempts"] = 0
        intent["fallback_used"] = True
        return intent

    prompt = f"""
You are the intent router for OpsPilot.

Classify the input into a workflow. The only supported workflow today is:
- customer_feedback_triage

Return JSON only with:
- workflow_type: always "customer_feedback_triage"
- confidence: number from 0.0 to 1.0
- reason: short explanation
- requires_clarification: true if the input is too vague to triage confidently

Input:
{input_text.strip()}
""".strip()

    retry_result = retry_with_fallback(
        operation=lambda: generate_json(prompt, INTENT_RESPONSE_SCHEMA),
        fallback=lambda: _fallback_intent(
            "Gemini intent router unavailable. Falling back to safe clarification mode."
        ),
        max_retries=2,
    )

    if retry_result["fallback_used"]:
        intent = retry_result["result"] or _fallback_intent(
            "Gemini intent router unavailable. Falling back to safe clarification mode."
        )
    else:
        intent = _normalize_intent(retry_result["result"])

    intent["attempts"] = retry_result["attempts"]
    intent["fallback_used"] = retry_result["fallback_used"]

    return intent
