from app.agents.nodes.planner_node import plan_next_actions

context = {
    "workflow_type": "customer_feedback_triage",
    "issue": {"category": "billing", "title": "Invoice unpaid after payment"},
    "requires_clarification": False,
    "memory_matches": [{"title": "Similar billing issue"}],
    "incident_detected": False,
    "confidence": 0.82,
    "fallback_used": False,
}

print(plan_next_actions(context))