RISK_KEYWORDS = {
    "refund": "refund/payment risk",
    "payment": "refund/payment risk",
    "invoice": "billing risk",
    "billing": "billing risk",
    "charge": "billing risk",
    "auth": "auth risk",
    "login": "auth risk",
    "account access": "auth risk",
    "security": "security risk",
    "data loss": "security risk",
}


def _clean_text(value: object, default: str) -> str:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return default


def _yes_no(value: bool) -> str:
    return "yes" if value else "no"


def _fallback_used(tool_calls: list[dict] | None, reply: dict) -> bool:
    if reply.get("fallback_used"):
        return True

    if not tool_calls:
        return False

    return any(bool(tool_call.get("fallback_used")) for tool_call in tool_calls)


def _provider_note(tool_calls: list[dict] | None, fallback_used: bool) -> str:
    if fallback_used:
        return "fallback/local provider was used"

    if not tool_calls:
        return "no fallback/local provider was recorded"

    providers = {
        tool_call.get("provider")
        for tool_call in tool_calls
        if tool_call.get("provider")
    }

    if providers == {"local"}:
        return "local provider was used as the primary path"

    if "local" in providers:
        return "local provider was used for part of the run"

    return "no fallback/local provider was recorded"


def _risk_topics(issue: dict, ticket: dict, reply: dict) -> list[str]:
    haystack = " ".join(
        _clean_text(value, "")
        for value in [
            issue.get("title"),
            issue.get("category"),
            issue.get("description"),
            ticket.get("category"),
            ticket.get("description"),
            reply.get("issue"),
            reply.get("risk_reason"),
        ]
    ).lower()

    topics = []
    for keyword, label in RISK_KEYWORDS.items():
        if keyword in haystack and label not in topics:
            topics.append(label)

    return topics


def _numbered_actions(actions: list[str]) -> str:
    return "\n".join(f"{index}. {action}" for index, action in enumerate(actions, start=1))


def _source_workflow_ids(memory_matches: list[dict] | None) -> list[int]:
    if not memory_matches:
        return []

    workflow_ids = []
    for memory_match in memory_matches:
        workflow_id = memory_match.get("workflow_run_id")
        if isinstance(workflow_id, int) and workflow_id not in workflow_ids:
            workflow_ids.append(workflow_id)

    return workflow_ids


def generate_founder_summary(
    issue: dict,
    ticket: dict,
    reply: dict,
    evaluation: dict,
    tool_calls: list[dict] | None = None,
    memory_matches: list[dict] | None = None,
) -> dict:
    category = _clean_text(issue.get("category"), _clean_text(ticket.get("category"), "unknown"))
    customer = _clean_text(issue.get("customer") or reply.get("customer"), "unknown customer")
    priority = _clean_text(ticket.get("priority") or issue.get("severity"), "medium")
    human_review_required = bool(
        evaluation.get("requires_human_review")
        or reply.get("requires_approval")
        or reply.get("risk_level") in {"medium", "high"}
    )
    fallback_used = _fallback_used(tool_calls, reply)
    provider_note = _provider_note(tool_calls, fallback_used)

    memory_count = len(memory_matches or [])
    source_workflow_ids = _source_workflow_ids(memory_matches)
    source_workflow_note = (
        f" from workflow #{source_workflow_ids[0]}"
        if len(source_workflow_ids) == 1
        else f" from workflows {', '.join(f'#{workflow_id}' for workflow_id in source_workflow_ids)}"
        if source_workflow_ids
        else ""
    )
    memory_note = (
        f"{memory_count} similar past issue{'s' if memory_count != 1 else ''}{source_workflow_note} were found, increasing recurrence risk and priority"
        if memory_count
        else "no related past issues were found"
    )

    summary = (
        f"OpsPilot detected a {category} issue for {customer}. "
        f"The generated ticket is {priority} priority, human review required: "
        f"{_yes_no(human_review_required)}, {provider_note}, and {memory_note}."
    )

    risks = []
    topics = _risk_topics(issue, ticket, reply)
    if topics:
        risks.append(f"Relevant risk areas: {', '.join(topics)}.")

    reply_risk = reply.get("risk_level")
    if reply_risk in {"medium", "high"}:
        risks.append(f"Customer reply carries {reply_risk} risk and should be reviewed before sending.")

    if fallback_used:
        risks.append("Provider fallback/local execution was used, so review output quality before customer-facing action.")

    evaluation_risks = _clean_text(evaluation.get("risks"), "")
    if evaluation_risks:
        risks.append(evaluation_risks)

    if memory_count:
        risks.append(
            "Memory increased priority/risk because similar past issues "
            f"{source_workflow_note.strip()} indicate this may be recurring rather than isolated."
        )

    if not risks:
        risks.append("No major business or provider execution risks were detected.")

    actions = [
        "Review and approve or reject the generated customer reply.",
        "Assign the generated ticket to the owning engineering team.",
        "Validate the customer evidence against product or support records.",
    ]

    if category in {"billing", "auth", "security"} or topics:
        actions.append("Escalate the sensitive customer-impacting risk to the appropriate owner.")

    if fallback_used:
        actions.append("Spot-check the fallback/local provider output for accuracy before relying on it.")

    if memory_count:
        actions.append("Compare against the similar past issue workflows before final prioritization.")

    if len(actions) < 5:
        actions.append("Track the run outcome and update the customer once the next step is confirmed.")

    return {
        "summary": summary,
        "risks": " ".join(risks),
        "recommended_actions": _numbered_actions(actions[:5]),
    }
