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


def _issue_category(context: dict) -> str:
    issue = context.get("issue")
    if not isinstance(issue, dict):
        return ""
    category = issue.get("category")
    return category.strip().lower() if isinstance(category, str) else ""


def plan_next_actions(context: dict) -> dict:
    context = context if isinstance(context, dict) else {}
    category = _issue_category(context)
    requires_human_approval = category in SENSITIVE_CATEGORIES

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
    }
