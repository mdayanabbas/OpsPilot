SENSITIVE_CATEGORIES = {"billing", "auth", "security"}
BILLING_MANUAL_REVIEW_TERMS = {
    "refund",
    "charged twice",
    "duplicate charge",
    "payment",
    "invoice",
    "billing",
    "subscription inactive",
}
REFUND_PROMISE_TERMS = {
    "refund",
    "refunded",
    "reimburse",
    "reimbursement",
    "reverse the payment",
    "payment reversal",
    "reverse the charge",
    "chargeback",
}


def _append_unique(values: list[str], value: str) -> None:
    if value not in values:
        values.append(value)


def _as_dict(value: object) -> dict:
    return value if isinstance(value, dict) else {}


def _as_list(value: object) -> list:
    return value if isinstance(value, list) else []


def _clean_text(value: object) -> str:
    return value.strip() if isinstance(value, str) and value.strip() else ""


def _issue_category(issue: dict) -> str:
    return _clean_text(issue.get("category")).lower()


def _combined_manual_review_text(issue: dict, ticket: dict, reply: dict) -> str:
    issue_text = " ".join(
        _clean_text(issue.get(key))
        for key in ("title", "category", "description", "customer")
    )
    return " ".join(
        [
            issue_text,
            _clean_text(ticket.get("title")),
            _clean_text(reply.get("issue")),
        ]
    ).lower()


def _billing_manual_review_triggered(issue: dict, ticket: dict, reply: dict) -> bool:
    haystack = _combined_manual_review_text(issue, ticket, reply)
    return any(term in haystack for term in BILLING_MANUAL_REVIEW_TERMS)


def _planner_requires_human_review(context: dict) -> bool:
    planner_decision = _as_dict(context.get("planner_decision"))
    return planner_decision.get("plan_type") == "human_review"


def _has_acceptance_criteria(ticket: dict) -> bool:
    criteria = ticket.get("acceptance_criteria")
    if isinstance(criteria, list):
        return any(isinstance(item, str) and item.strip() for item in criteria)
    if isinstance(criteria, str):
        return bool(criteria.strip())
    return False


def _score_below(value: object, threshold: float) -> bool:
    try:
        return float(value) < threshold
    except (TypeError, ValueError):
        return False


def _score_above(value: object, threshold: float) -> bool:
    try:
        return float(value) > threshold
    except (TypeError, ValueError):
        return False


def _provider_issue_detected(context: dict) -> bool:
    if context.get("fallback_used") is True:
        return True

    for tool_call in _as_list(context.get("tool_calls")):
        if not isinstance(tool_call, dict):
            continue
        if tool_call.get("fallback_used") is True:
            return True
        if tool_call.get("status") in {"failed", "error"}:
            return True
        if tool_call.get("error_message"):
            return True

    return False


def _recommended_action(
    critic_status: str,
    risk_flags: list[str],
    quality_notes: list[str],
) -> str:
    if critic_status == "blocked":
        return "Block customer-facing action until a human reviews and approves the reply."
    if risk_flags or quality_notes:
        return "Route this workflow for manual review before sending customer-facing output."
    return "Proceed with the generated workflow outputs."


def critique_workflow_output(context: dict) -> dict:
    context = context if isinstance(context, dict) else {}
    issue = _as_dict(context.get("issue"))
    ticket = _as_dict(context.get("ticket"))
    reply = _as_dict(context.get("reply"))
    evaluation = _as_dict(context.get("evaluation"))
    planner_requires_human_review = _planner_requires_human_review(context)

    risk_flags = []
    quality_notes = []
    blocked = False

    reply_requires_approval = reply.get("requires_approval") is True
    ticket_requires_approval = ticket.get("requires_approval") is True
    draft_reply_text = _clean_text(reply.get("draft_reply")).lower()

    if any(term in draft_reply_text for term in REFUND_PROMISE_TERMS) and not reply_requires_approval:
        blocked = True
        risk_flags.append("Reply appears to promise refund or payment reversal without approval.")

    category = _issue_category(issue)
    if category in SENSITIVE_CATEGORIES and not (reply_requires_approval or ticket_requires_approval):
        risk_flags.append(f"{category} issue is missing an approval requirement.")

    if _billing_manual_review_triggered(issue, ticket, reply):
        print("[critic_node] billing/manual review warning triggered")
        _append_unique(risk_flags, "billing_risk")
        _append_unique(risk_flags, "refund_escalation_risk")
        _append_unique(risk_flags, "customer_impact_risk")
        quality_notes.append(
            "Billing, refund, payment, invoice, duplicate charge, or subscription-impacting language requires manual review."
        )

    if planner_requires_human_review:
        quality_notes.append("Planner selected human_review, so critic cannot pass this workflow automatically.")

    if not _has_acceptance_criteria(ticket):
        quality_notes.append("Ticket lacks acceptance criteria.")

    if _score_below(evaluation.get("quality_score"), 0.75):
        quality_notes.append("Evaluation quality score is below 0.75.")

    if _score_above(evaluation.get("unsupported_claim_rate"), 0.2):
        risk_flags.append("Unsupported claim rate is above 0.20.")

    if _provider_issue_detected(context):
        risk_flags.append("Fallback execution or provider failure was detected.")

    if blocked:
        critic_status = "blocked"
    elif risk_flags or quality_notes:
        critic_status = "warning"
    else:
        critic_status = "passed"

    requires_manual_review = critic_status in {"blocked", "warning"}

    return {
        "critic_status": critic_status,
        "risk_flags": risk_flags,
        "quality_notes": quality_notes,
        "recommended_action": _recommended_action(
            critic_status,
            risk_flags,
            quality_notes,
        ),
        "requires_manual_review": requires_manual_review,
    }
