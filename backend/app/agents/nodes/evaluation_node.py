REQUIRED_ISSUE_FIELDS = ("title", "category", "severity", "description")
REQUIRED_TICKET_FIELDS = (
    "title",
    "priority",
    "team",
    "category",
    "description",
    "acceptance_criteria",
)
REQUIRED_REPLY_FIELDS = (
    "issue",
    "risk_level",
    "requires_approval",
)

SENSITIVE_TERMS = {
    "account",
    "billing",
    "data loss",
    "invoice",
    "legal",
    "login",
    "password",
    "payment",
    "refund",
    "refunds",
    "security",
}

RISKY_REPLY_TERMS = {
    "refund",
    "refunded",
    "liable",
    "liability",
    "fixed",
    "resolved",
    "internal log",
    "logs show",
}


def _clamp_score(value: float) -> float:
    return round(max(0.0, min(1.0, value)), 2)


def _has_value(data: dict, field: str) -> bool:
    value = data.get(field)
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, list):
        return bool(value)
    return value is not None


def _missing_count(data: dict, fields: tuple[str, ...]) -> int:
    if not isinstance(data, dict):
        return len(fields)
    return sum(1 for field in fields if not _has_value(data, field))


def _acceptance_criteria_count(ticket: dict) -> int:
    criteria = ticket.get("acceptance_criteria") if isinstance(ticket, dict) else None
    if isinstance(criteria, list):
        return len([item for item in criteria if isinstance(item, str) and item.strip()])
    if isinstance(criteria, str):
        return len([line for line in criteria.splitlines() if line.strip()])
    return 0


def _combined_text(*items: dict) -> str:
    parts = []
    for item in items:
        if not isinstance(item, dict):
            continue
        parts.extend(str(value) for value in item.values() if value is not None)
    return " ".join(parts).lower()


def _is_safe_fallback_reply(reply: dict) -> bool:
    if not isinstance(reply, dict):
        return True

    risk_reason = str(reply.get("risk_reason") or "").lower()
    draft_reply = str(reply.get("draft_reply") or "").lower()

    return (
        "conservative fallback" in risk_reason
        or "will follow up after we understand the right next step" in draft_reply
    )


def _tool_recovery_success(reply: dict, fallback_used: bool) -> float:
    if not fallback_used:
        return 1.0
    if _is_safe_fallback_reply(reply):
        return 0.4
    return 0.7


def _requires_human_review(issue: dict, ticket: dict, reply: dict) -> bool:
    issue_category = issue.get("category") if isinstance(issue, dict) else None
    if issue_category in {"billing", "auth"}:
        return True

    text = _combined_text(issue, ticket, reply)
    risk_level = reply.get("risk_level") if isinstance(reply, dict) else None

    return (
        any(term in text for term in SENSITIVE_TERMS)
        or risk_level == "high"
    )


def _risk_notes(
    issue: dict,
    ticket: dict,
    reply: dict,
    fallback_used: bool,
) -> list[str]:
    notes = []

    missing_issue = _missing_count(issue, REQUIRED_ISSUE_FIELDS)
    missing_ticket = _missing_count(ticket, REQUIRED_TICKET_FIELDS)
    missing_reply = _missing_count(reply, REQUIRED_REPLY_FIELDS)

    if missing_issue:
        notes.append(f"Missing {missing_issue} issue field(s).")
    if missing_ticket:
        notes.append(f"Missing {missing_ticket} ticket field(s).")
    if missing_reply:
        notes.append(f"Missing {missing_reply} reply field(s).")
    if _acceptance_criteria_count(ticket) == 0:
        notes.append("Ticket has no acceptance criteria.")
    if fallback_used:
        notes.append("A fallback path was used.")
    if _requires_human_review(issue, ticket, reply):
        notes.append("Human review required due to sensitive or high-risk content.")

    return notes


def evaluate_workflow_output(
    issue: dict,
    ticket: dict,
    reply: dict,
    fallback_used: bool = False,
) -> dict:
    issue = issue if isinstance(issue, dict) else {}
    ticket = ticket if isinstance(ticket, dict) else {}
    reply = reply if isinstance(reply, dict) else {}

    missing_issue = _missing_count(issue, REQUIRED_ISSUE_FIELDS)
    missing_ticket = _missing_count(ticket, REQUIRED_TICKET_FIELDS)
    missing_reply = _missing_count(reply, REQUIRED_REPLY_FIELDS)

    acceptance_criteria_count = _acceptance_criteria_count(ticket)
    risky_reply_hits = sum(
        1
        for term in RISKY_REPLY_TERMS
        if term in _combined_text(reply)
    )

    ticket_completeness = 1.0
    ticket_completeness -= missing_ticket * 0.12
    if acceptance_criteria_count == 0:
        ticket_completeness -= 0.25
    elif acceptance_criteria_count < 2:
        ticket_completeness -= 0.10

    reply_policy_compliance = 1.0
    reply_policy_compliance -= missing_reply * 0.15
    reply_policy_compliance -= risky_reply_hits * 0.12
    if reply.get("risk_level") == "high":
        reply_policy_compliance -= 0.10

    unsupported_claim_rate = _clamp_score(
        0.05 + (risky_reply_hits * 0.10) + (missing_issue * 0.05)
    )

    tool_recovery_success = _tool_recovery_success(reply, fallback_used)

    quality_score = 1.0
    quality_score -= missing_issue * 0.08
    quality_score -= missing_ticket * 0.08
    quality_score -= missing_reply * 0.08
    quality_score -= risky_reply_hits * 0.08
    if acceptance_criteria_count == 0:
        quality_score -= 0.15
    if fallback_used:
        quality_score -= 0.07

    requires_human_review = _requires_human_review(issue, ticket, reply)
    risks = " ".join(_risk_notes(issue, ticket, reply, fallback_used))
    if not risks:
        risks = "No major risks detected by heuristic evaluator."

    return {
        "quality_score": _clamp_score(quality_score),
        "reply_policy_compliance": _clamp_score(reply_policy_compliance),
        "ticket_completeness": _clamp_score(ticket_completeness),
        "unsupported_claim_rate": unsupported_claim_rate,
        "tool_recovery_success": tool_recovery_success,
        "requires_human_review": requires_human_review,
        "risks": risks,
    }
