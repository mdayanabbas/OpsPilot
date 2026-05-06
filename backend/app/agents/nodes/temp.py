from app.agents.nodes.evaluation_node import evaluate_workflow_output

issue = {
    "title": "Invoice unpaid after payment",
    "category": "billing",
    "severity": "medium",
    "customer": "Acme Corp",
    "description": "Customer says invoice still shows unpaid even after successful payment.",
}

ticket = {
    "title": "Fix invoice status sync after successful payment",
    "priority": "medium",
    "team": "backend",
    "category": "billing",
    "description": "Investigate why invoice status remains unpaid after payment.",
    "acceptance_criteria": [
        "Invoice status updates correctly after payment",
        "Billing sync errors are logged",
    ],
}

reply = {
    "customer": "Acme Corp",
    "issue": "Invoice unpaid after payment",
    "draft_reply": "Thanks for flagging this. We are investigating the billing status issue and will follow up after review.",
    "risk_level": "medium",
    "risk_reason": "Billing-related issue requires review.",
    "requires_approval": True,
}

print(
    evaluate_workflow_output(
        issue=issue,
        ticket=ticket,
        reply=reply,
        fallback_used=False,
    )
)