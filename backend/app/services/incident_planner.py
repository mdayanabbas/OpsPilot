"""Deterministic, read-only response planning for detected incidents."""


PLAN_TOOLS = {
    "billing_incident": [
        "search_memory",
        "generate_founder_summary",
        "send_incident_alert",
    ],
    "auth_incident": [
        "search_memory",
        "generate_founder_summary",
        "send_incident_alert",
    ],
    "performance_incident": [
        "search_memory",
        "generate_founder_summary",
    ],
    "general_incident": [
        "search_memory",
        "generate_founder_summary",
    ],
}


def _value(source, key: str, default=None):
    if isinstance(source, dict):
        return source.get(key, default)
    return getattr(source, key, default)


def _plan_type(category: str) -> str:
    if category == "billing":
        return "billing_incident"
    if category == "auth":
        return "auth_incident"
    if category == "performance":
        return "performance_incident"
    return "general_incident"


def create_incident_response_plan(incident, intelligence) -> dict:
    """Build a deterministic plan without executing any selected tool."""
    category = str(_value(incident, "category", "other") or "other").lower()
    plan_type = _plan_type(category)
    intelligence = intelligence if isinstance(intelligence, dict) else {}
    risks = intelligence.get("operational_risks")
    risks = risks if isinstance(risks, list) else []
    clusters = intelligence.get("root_cause_clusters")
    clusters = clusters if isinstance(clusters, list) else []
    workflow_count = int(_value(incident, "workflow_count", 0) or 0)
    severity = str(_value(incident, "severity", "unknown") or "unknown")

    reasoning_parts = [
        f"Selected {plan_type} for a {severity} {category} incident affecting {workflow_count} workflow(s).",
        "The plan is advisory and does not execute tools automatically.",
    ]
    if clusters:
        reasoning_parts.append(
            f"Incident intelligence identified {len(clusters)} root-cause cluster(s)."
        )
    if risks:
        reasoning_parts.append(
            f"Operational risks include: {', '.join(str(risk) for risk in risks[:3])}."
        )
    if plan_type in {"billing_incident", "auth_incident"}:
        reasoning_parts.append(
            "The sensitive incident category includes an internal alert as a proposed human-reviewed action."
        )

    return {
        "plan_type": plan_type,
        "next_tools": list(PLAN_TOOLS[plan_type]),
        "reasoning": " ".join(reasoning_parts),
    }
