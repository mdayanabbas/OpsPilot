import json

from app.services.gemini_service import generate_json
from app.tools.retry_controller import retry_with_fallback


VALID_RISK_LEVELS = {"low", "medium", "high"}
HIGH_RISK_TERMS = {
    "refund",
    "legal",
    "lawsuit",
    "billing",
    "account access",
    "payment",
    "data loss",
    "security",
    "policy",
}

REPLY_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "customer": {"type": "string", "nullable": True},
        "issue": {"type": "string"},
        "draft_reply": {"type": "string", "nullable": True},
        "risk_level": {"type": "string"},
        "risk_reason": {"type": "string", "nullable": True},
        "requires_approval": {"type": "boolean"},
    },
    "required": [
        "customer",
        "issue",
        "draft_reply",
        "risk_level",
        "risk_reason",
        "requires_approval",
    ],
}


def _clean_text(value: object, default: str) -> str:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return default


def _clean_optional_text(value: object) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _issue_text(issue: dict) -> str:
    title = _clean_text(issue.get("title"), "Customer issue")
    description = _clean_text(
        issue.get("description"),
        "Customer reported an issue that needs review.",
    )
    return f"{title}: {description}"


def _is_sensitive_issue(issue: dict) -> bool:
    category = issue.get("category")
    if category in {"billing", "auth"}:
        return True

    haystack = " ".join(
        str(issue.get(key, ""))
        for key in ("title", "category", "description")
    ).lower()
    return any(term in haystack for term in HIGH_RISK_TERMS)


def _fallback_reply(issue: dict) -> dict:
    customer = _clean_optional_text(issue.get("customer"))
    issue_text = _issue_text(issue)

    return {
        "customer": customer,
        "issue": issue_text,
        "draft_reply": (
            "Thanks for sharing this with us. We are reviewing the issue and "
            "will follow up after we understand the right next step."
        ),
        "risk_level": "medium",
        "risk_reason": "Generated as a conservative fallback and should be reviewed before sending.",
        "requires_approval": True,
        "provider": "fallback",
        "fallback_used": True,
    }


def _normalize_risk_level(raw_level: object, issue: dict) -> str:
    risk_level = raw_level if raw_level in VALID_RISK_LEVELS else "medium"
    if _is_sensitive_issue(issue) and risk_level == "low":
        return "medium"
    return risk_level


def _normalize_reply(raw_reply: dict, issue: dict) -> dict:
    fallback = _fallback_reply(issue)
    if not isinstance(raw_reply, dict):
        return fallback

    risk_level = _normalize_risk_level(raw_reply.get("risk_level"), issue)
    risk_reason = _clean_optional_text(raw_reply.get("risk_reason"))
    if _is_sensitive_issue(issue) and not risk_reason:
        risk_reason = "Issue involves a sensitive customer or account-impacting topic and needs review."

    draft_reply = _clean_optional_text(raw_reply.get("draft_reply"))
    if not draft_reply and risk_level != "high":
        draft_reply = fallback["draft_reply"]

    return {
        "customer": _clean_optional_text(raw_reply.get("customer"))
        or fallback["customer"],
        "issue": _clean_text(raw_reply.get("issue"), fallback["issue"]),
        "draft_reply": draft_reply,
        "risk_level": risk_level,
        "risk_reason": risk_reason,
        "requires_approval": True,
        "provider": raw_reply.get("provider", "gemini"),
        "fallback_used": raw_reply.get("fallback_used", False),
    }


def generate_customer_reply(issue: dict) -> dict:
    if not isinstance(issue, dict):
        fallback = _fallback_reply({})
        fallback["attempts"] = 0
        return fallback

    prompt_issue = {
        "title": _clean_text(issue.get("title"), "Customer issue"),
        "category": _clean_text(issue.get("category"), "other"),
        "severity": _clean_text(issue.get("severity"), "medium"),
        "customer": issue.get("customer"),
        "description": _clean_text(
            issue.get("description"),
            "Customer reported an issue that needs review.",
        ),
    }

    prompt = f"""
You draft safe customer support replies for OpsPilot.

Return JSON only. The reply is only a draft and always requires approval.

Rules:
- risk_level must be one of: low, medium, high
- requires_approval must be true
- if the issue involves refund, legal threat, billing, account access, payment,
  data loss, security, or policy promise, risk_level must be medium or high and
  risk_reason must explain why review is needed
- do not promise refunds
- do not admit liability
- do not claim a fix is complete
- do not mention internal tools or logs directly
- do not imply anything is sent automatically
- if risk is too high, set draft_reply to null

Issue:
{json.dumps(prompt_issue)}
""".strip()

    retry_result = retry_with_fallback(
        operation=lambda: generate_json(prompt, REPLY_RESPONSE_SCHEMA),
        fallback=lambda: _fallback_reply(issue),
        max_retries=2,
    )

    if retry_result["fallback_used"]:
        reply = retry_result["result"] or _fallback_reply(issue)
    else:
        reply = _normalize_reply(retry_result["result"], issue)

    reply["attempts"] = retry_result["attempts"]
    reply["fallback_used"] = reply.get("fallback_used", retry_result["fallback_used"])
    reply["provider"] = reply.get(
        "provider",
        "fallback" if reply["fallback_used"] else "gemini",
    )

    return reply
