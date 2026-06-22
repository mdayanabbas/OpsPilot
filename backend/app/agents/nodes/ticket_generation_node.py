import json

from app.agents.nodes.issue_normalization_node import normalize_priority
from app.services.gemini_service import GeminiServiceError, generate_json


CATEGORY_TO_TEAM = {
    "billing": "backend",
    "auth": "backend",
    "ui": "frontend",
    "performance": "backend",
    "data": "backend",
    "integration": "backend",
    "notification": "backend",
    "security": "backend",
    "other": "backend",
}

VALID_PRIORITIES = {"low", "medium", "high"}

TICKET_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "priority": {"type": "string"},
        "team": {"type": "string"},
        "category": {"type": "string"},
        "description": {"type": "string"},
        "acceptance_criteria": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "required": [
        "title",
        "priority",
        "team",
        "category",
        "description",
        "acceptance_criteria",
    ],
}


def _clean_text(value: object, default: str) -> str:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return default


def _priority_from_issue(issue: dict) -> str:
    severity = issue.get("severity")
    current = severity if severity in VALID_PRIORITIES else "medium"
    issue_text = " ".join(
        str(issue.get(key, "")) for key in ("title", "description")
    )
    return normalize_priority(issue.get("category", "other"), issue_text, current)


def _team_from_category(category: str) -> str:
    return CATEGORY_TO_TEAM.get(category, "backend")


def _fallback_ticket(issue: dict) -> dict:
    category = issue.get("category")
    if category not in CATEGORY_TO_TEAM:
        category = "other"

    title = _clean_text(issue.get("title"), "Investigate customer issue")
    description = _clean_text(
        issue.get("description"),
        "Customer feedback requires investigation.",
    )

    return {
        "title": title,
        "priority": _priority_from_issue(issue),
        "team": _team_from_category(category),
        "category": category,
        "description": description,
        "acceptance_criteria": [
            "Reproduce or verify the reported issue.",
            "Identify the likely root cause.",
            "Confirm the fix or next action with supporting evidence.",
        ],
        "attempts": 1,
        "fallback_used": True,
        "provider": "fallback",
    }


def _normalize_acceptance_criteria(value: object) -> list[str]:
    if not isinstance(value, list):
        return []

    criteria = []
    for item in value:
        if isinstance(item, str) and item.strip():
            criteria.append(item.strip())

    return criteria


def _normalize_ticket(raw_ticket: dict, issue: dict) -> dict:
    fallback = _fallback_ticket(issue)

    if not isinstance(raw_ticket, dict):
        return fallback

    category = issue.get("category")
    if category not in CATEGORY_TO_TEAM:
        category = raw_ticket.get("category")
    if category not in CATEGORY_TO_TEAM:
        category = fallback["category"]

    priority = _priority_from_issue(issue)
    acceptance_criteria = _normalize_acceptance_criteria(
        raw_ticket.get("acceptance_criteria")
    )
    if not acceptance_criteria:
        acceptance_criteria = fallback["acceptance_criteria"]

    return {
        "title": _clean_text(raw_ticket.get("title"), fallback["title"]),
        "priority": priority,
        "team": _team_from_category(category),
        "category": category,
        "description": _clean_text(
            raw_ticket.get("description"),
            fallback["description"],
        ),
        "acceptance_criteria": acceptance_criteria,
        "attempts": raw_ticket.get("attempts", 1),
        "fallback_used": raw_ticket.get("fallback_used", False),
        "provider": raw_ticket.get("provider", "gemini"),
    }


def generate_ticket(issue: dict) -> dict:
    if not isinstance(issue, dict):
        return _fallback_ticket({})

    fallback = _fallback_ticket(issue)
    prompt_issue = {
        "title": fallback["title"],
        "category": fallback["category"],
        "severity": fallback["priority"],
        "customer": issue.get("customer"),
        "description": fallback["description"],
    }

    prompt = f"""
You create concise engineering tickets for OpsPilot from extracted customer issues.

Use the issue details to generate a practical ticket. Keep the output JSON only.

Rules:
- priority must match issue severity: low, medium, or high
- team must follow category mapping:
  - billing -> backend
  - auth -> backend
  - ui -> frontend
  - performance -> backend
  - data -> backend
  - integration -> backend
  - notification -> backend
  - security -> backend
  - other -> backend
- acceptance_criteria must be a list of short, testable strings

Issue:
{json.dumps(prompt_issue)}
""".strip()

    try:
        ticket = generate_json(prompt, TICKET_RESPONSE_SCHEMA)
    except (GeminiServiceError, ValueError, TypeError):
        return fallback

    return _normalize_ticket(ticket, issue)
