from app.services.local_llm_service import generate_json_local

prompt = """
Classify this input for OpsPilot:

Input:
Acme Corp says invoice still shows unpaid after successful payment.

Return:
workflow_type, confidence, reason, requires_clarification
"""

schema = {
    "type": "object",
    "properties": {
        "workflow_type": {"type": "string"},
        "confidence": {"type": "number"},
        "reason": {"type": "string"},
        "requires_clarification": {"type": "boolean"},
    },
    "required": ["workflow_type", "confidence", "reason", "requires_clarification"],
}

print(generate_json_local(prompt, schema))