from app.agents.nodes.planner_node import generate_llm_plan, plan_next_actions


DEBUG_CONTEXT = {
    "workflow_type": "customer_feedback_triage",
    "issue": {
        "title": "Customers cannot export invoices",
        "description": "Several customers report invoice exports timing out.",
        "category": "billing",
        "severity": "high",
        "customer": "Acme Co",
    },
    "memory_matches": [
        {
            "workflow_run_id": 42,
            "title": "Invoice export timeout after billing release",
            "category": "billing",
            "content": "Similar export failures after a billing service deployment.",
        }
    ],
    "evaluation": {
        "requires_human_review": False,
        "quality_score": 0.88,
    },
    "incident_detected": False,
    "incident_signals": {
        "similar_reports": 3,
        "time_window_minutes": 45,
    },
    "customer_impact": "Multiple customers blocked from invoice exports.",
    "confidence": 0.84,
    "requires_clarification": False,
    "fallback_used": False,
}


def main() -> None:
    print("Calling generate_llm_plan directly...")
    print(generate_llm_plan(DEBUG_CONTEXT))
    print("\nCalling plan_next_actions with validation/fallback...")
    print(plan_next_actions(DEBUG_CONTEXT))


if __name__ == "__main__":
    main()
