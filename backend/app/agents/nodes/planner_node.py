SENSITIVE_CATEGORIES = {"billing", "auth", "refund", "security"}

STANDARD_TRIAGE_TOOLS = [
    {
        "tool_name": "generate_ticket",
        "reason": "Create an engineering ticket for the actionable customer issue.",
        "priority": "high",
    },
    {
        "tool_name": "generate_customer_reply",
        "reason": "Draft a safe customer reply for review.",
        "priority": "high",
    },
    {
        "tool_name": "evaluate_workflow_output",
        "reason": "Evaluate ticket and reply quality before downstream summary.",
        "priority": "medium",
    },
    {
        "tool_name": "generate_founder_summary",
        "reason": "Summarize workflow outcome, risks, and recommended next actions.",
        "priority": "medium",
    },
]

INCIDENT_RESPONSE_TOOLS = [
    {
        "tool_name": "search_memory",
        "reason": "Find related past workflows that may explain the incident pattern.",
        "priority": "high",
    },
    {
        "tool_name": "generate_founder_summary",
        "reason": "Summarize incident context, business risk, and recommended response.",
        "priority": "high",
    },
    {
        "tool_name": "send_incident_alert",
        "reason": "Notify internal responders about the detected incident.",
        "priority": "high",
    },
]


def _issue_category(context: dict) -> str:
    issue = context.get("issue")
    if not isinstance(issue, dict):
        return ""
    category = issue.get("category")
    return category.strip().lower() if isinstance(category, str) else ""

    category = issue.get("category")
    if isinstance(category, str):
        return category.strip().lower()

    return ""


def _has_memory_matches(context: dict) -> bool:
    memory_matches = context.get("memory_matches")
    return isinstance(memory_matches, list) and bool(memory_matches)


def _requires_human_approval(context: dict) -> bool:
    category = _issue_category(context)
    if category in SENSITIVE_CATEGORIES:
        return True

    evaluation = context.get("evaluation")
    if isinstance(evaluation, dict) and evaluation.get("requires_human_review") is True:
        return True

    reply = context.get("reply")
    if isinstance(reply, dict) and reply.get("requires_approval") is True:
        return True

    return False


def _reasoning_summary(
    plan_type: str,
    context: dict,
    requires_human_approval: bool,
) -> str:
    parts = []

    if plan_type == "clarification":
        parts.append("Clarification is required before running tools.")
    elif plan_type == "incident_response":
        parts.append("Incident response selected because an incident was detected.")
    elif plan_type == "human_review":
        parts.append("Human review selected because the workflow requires approval.")
    else:
        parts.append("Standard triage selected for an actionable workflow issue.")

    category = _issue_category(context)
    if category in SENSITIVE_CATEGORIES:
        parts.append(f"Category '{category}' requires human approval.")
    elif requires_human_approval:
        parts.append("Existing workflow outputs indicate human approval is required.")

    if _has_memory_matches(context):
        parts.append(
            "search_memory context is present through memory matches and should inform prioritization and summary."
        )

    if context.get("fallback_used") is True:
        parts.append("Fallback execution was used, so outputs should be reviewed carefully.")

    return " ".join(parts)


def plan_next_actions(context: dict) -> dict:
    context = context if isinstance(context, dict) else {}
    category = _issue_category(context)
    requires_human_approval = category in SENSITIVE_CATEGORIES
    requires_human_approval = _requires_human_approval(context)

    if context.get("requires_clarification") is True:
        plan_type = "clarification"
        next_tools = []
    elif context.get("incident_detected") is True:
        plan_type = "incident_response"
        next_tools = [
            {
                "tool_name": "search_memory",
                "reason": "Find related past workflows that may explain the incident pattern.",
                "priority": "high",
            },
            {
                "tool_name": "generate_founder_summary",
                "reason": "Summarize incident context, business risk, and recommended response.",
                "priority": "high",
            },
            {
                "tool_name": "send_incident_alert",
                "reason": "Notify internal responders about the detected incident.",
                "priority": "high",
            },
        ]
        next_tools = INCIDENT_RESPONSE_TOOLS
    elif requires_human_approval:
        plan_type = "human_review"
        next_tools = STANDARD_TRIAGE_TOOLS
    else:
        plan_type = "standard_triage"
        next_tools = STANDARD_TRIAGE_TOOLS

    summary_parts = [f"Planner selected {plan_type}."]
    if requires_human_approval:
        summary_parts.append(f"Category '{category}' requires human approval.")
    if context.get("memory_matches"):
        summary_parts.append("Memory matches should inform prioritization and summary.")

    return {
        "plan_type": plan_type,
        "next_tools": [dict(tool) for tool in next_tools],
        "requires_human_approval": requires_human_approval,
        "reasoning_summary": " ".join(summary_parts),
        "reasoning_summary": _reasoning_summary(
            plan_type=plan_type,
            context=context,
            requires_human_approval=requires_human_approval,
        ),
    }
