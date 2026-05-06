from app.services.gemini_service import GeminiServiceError, generate_json


ISSUE_CATEGORIES = {"billing", "auth", "ui", "performance", "other"}
ISSUE_SEVERITIES = {"low", "medium", "high"}

ISSUE_EXTRACTION_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "issues": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "category": {"type": "string"},
                    "severity": {"type": "string"},
                    "customer": {"type": "string", "nullable": True},
                    "description": {"type": "string"},
                },
                "required": [
                    "title",
                    "category",
                    "severity",
                    "customer",
                    "description",
                ],
            },
        }
    },
    "required": ["issues"],
}


def _empty_issues() -> dict:
    return {"issues": []}


def _normalize_issue(raw_issue: dict) -> dict | None:
    if not isinstance(raw_issue, dict):
        return None

    title = raw_issue.get("title")
    description = raw_issue.get("description")
    if not isinstance(title, str) or not title.strip():
        return None
    if not isinstance(description, str) or not description.strip():
        return None

    category = raw_issue.get("category")
    if category not in ISSUE_CATEGORIES:
        category = "other"

    severity = raw_issue.get("severity")
    if severity not in ISSUE_SEVERITIES:
        severity = "medium"

    customer = raw_issue.get("customer")
    if not isinstance(customer, str) or not customer.strip():
        customer = None

    return {
        "title": title.strip(),
        "category": category,
        "severity": severity,
        "customer": customer,
        "description": description.strip(),
    }


def _normalize_issues(raw_result: dict) -> dict:
    raw_issues = raw_result.get("issues")
    if not isinstance(raw_issues, list):
        return _empty_issues()

    issues = []
    for raw_issue in raw_issues:
        issue = _normalize_issue(raw_issue)
        if issue:
            issues.append(issue)

    return {"issues": issues}


def extract_issues(input_text: str) -> dict:
    if not isinstance(input_text, str) or not input_text.strip():
        return _empty_issues()

    prompt = f"""
You extract actionable customer issues for OpsPilot.

Extract zero or more issues from the input. Keep categories limited to:
- billing
- auth
- ui
- performance
- other

Keep severity limited to:
- low
- medium
- high

Return JSON only in this shape:
{{
  "issues": [
    {{
      "title": "short issue title",
      "category": "billing | auth | ui | performance | other",
      "severity": "low | medium | high",
      "customer": "customer name if known, otherwise null",
      "description": "concise issue description"
    }}
  ]
}}

Input:
{input_text.strip()}
""".strip()

    try:
        result = generate_json(prompt, ISSUE_EXTRACTION_RESPONSE_SCHEMA)
    except (GeminiServiceError, ValueError, TypeError):
        return _empty_issues()

    return _normalize_issues(result)
