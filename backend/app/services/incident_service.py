import json
import re
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models.incident import Incident
from app.models.reply import CustomerReply
from app.models.ticket import Ticket
from app.models.workflow import WorkflowRun

THEME_RULES = [
    ("unpaid invoice", ("unpaid", "invoice")),
    ("duplicate charge", ("duplicate", "charge")),
    ("inactive subscription", ("inactive", "subscription")),
    ("login failures", ("login", "fail")),
    ("password reset issues", ("reset", "password")),
    ("slow dashboard", ("slow", "dashboard")),
    ("slow page", ("slow", "page")),
    ("timeout", ("timeout",)),
    ("refund request", ("refund",)),
]


def _severity(workflow_count: int) -> str:
    if workflow_count >= 8:
        return "critical"
    if workflow_count >= 5:
        return "high"
    return "medium"


def _incident_title(category: str) -> str:
    if category == "billing":
        return "Billing incident suspected"
    if category == "auth":
        return "Authentication incident suspected"
    if category == "performance":
        return "Performance degradation incident"
    return f"{category.title()} incident suspected"


def _clean_tokens(value: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", value.lower())
        if len(token) >= 3
    }


def _combined_text(ticket: Ticket, replies_by_workflow: dict[int, list[CustomerReply]]) -> str:
    reply_text = " ".join(
        reply.issue or ""
        for reply in replies_by_workflow.get(ticket.workflow_run_id, [])
    )
    return " ".join(
        value
        for value in [ticket.title, ticket.description, reply_text]
        if value
    )


def _detect_theme(text: str, category: str) -> str:
    lowered = text.lower()
    tokens = _clean_tokens(lowered)

    for theme, keywords in THEME_RULES:
        if all(any(keyword in token or token in keyword for token in tokens) for keyword in keywords):
            return theme

    if category == "billing":
        return "billing workflow disruption"
    if category == "auth":
        return "authentication access disruption"
    if category == "performance":
        return "performance degradation"
    return f"{category} issue cluster"


def generate_incident_intelligence(
    category: str,
    tickets: list[Ticket],
    replies_by_workflow: dict[int, list[CustomerReply]],
) -> dict:
    cluster_counts: dict[str, int] = {}
    combined_text = []

    for ticket in tickets:
        text = _combined_text(ticket, replies_by_workflow)
        combined_text.append(text)
        theme = _detect_theme(text, category)
        cluster_counts[theme] = cluster_counts.get(theme, 0) + 1

    root_cause_clusters = [
        {
            "theme": theme,
            "workflow_count": count,
            "summary": f"{count} workflow{'s' if count != 1 else ''} mention {theme}.",
        }
        for theme, count in sorted(cluster_counts.items(), key=lambda item: item[1], reverse=True)
    ]

    haystack = " ".join(combined_text).lower()
    operational_risks = []
    recommended_actions = [
        "Review the latest affected workflows and confirm whether the spike is still active.",
        "Assign an owner to validate the suspected incident category.",
    ]

    if category == "billing":
        if "refund" in haystack:
            operational_risks.append("refund escalation risk")
            recommended_actions.append("Prepare a refund escalation path for affected customers.")
        if "unpaid" in haystack:
            operational_risks.append("payment sync issue")
            recommended_actions.append("Inspect payment webhook and invoice synchronization logs.")
        if "inactive subscription" in haystack or ("inactive" in haystack and "subscription" in haystack):
            operational_risks.append("activation pipeline issue")
            recommended_actions.append("Audit subscription activation and entitlement update jobs.")

    if category == "auth":
        if "login" in haystack and any(term in haystack for term in ("fail", "failed", "failure")):
            operational_risks.append("authentication outage")
            recommended_actions.append("Check auth provider health, login error rates, and recent auth releases.")
        if "reset" in haystack and "password" in haystack:
            operational_risks.append("password reset instability")
            recommended_actions.append("Validate password reset email delivery and token verification.")

    if category == "performance":
        if "slow" in haystack and "page" in haystack:
            operational_risks.append("latency degradation")
            recommended_actions.append("Review page latency, API timings, and frontend performance traces.")
        if "timeout" in haystack:
            operational_risks.append("infrastructure instability")
            recommended_actions.append("Inspect timeout rates, database latency, and upstream dependency health.")

    if not operational_risks:
        operational_risks.append("recurring customer-impacting issue")
        recommended_actions.append("Compare ticket details to identify the common failing path.")

    recommended_actions.append("Send a concise internal incident update with scope, owner, and next checkpoint.")

    return {
        "root_cause_clusters": root_cause_clusters,
        "operational_risks": list(dict.fromkeys(operational_risks)),
        "recommended_actions": list(dict.fromkeys(recommended_actions))[:5],
    }


def detect_incidents(db: Session) -> Incident | None:
    window_start = datetime.utcnow() - timedelta(minutes=30)
    recent_tickets = (
        db.query(Ticket)
        .join(WorkflowRun, WorkflowRun.id == Ticket.workflow_run_id)
        .filter(
            WorkflowRun.created_at >= window_start,
            Ticket.category.isnot(None),
        )
        .all()
    )
    workflow_ids = {ticket.workflow_run_id for ticket in recent_tickets}
    replies = (
        db.query(CustomerReply)
        .filter(CustomerReply.workflow_run_id.in_(workflow_ids))
        .all()
        if workflow_ids
        else []
    )
    replies_by_workflow: dict[int, list[CustomerReply]] = {}
    for reply in replies:
        replies_by_workflow.setdefault(reply.workflow_run_id, []).append(reply)

    tickets_by_category: dict[str, list[Ticket]] = {}
    for ticket in recent_tickets:
        category = ticket.category or "uncategorized"
        tickets_by_category.setdefault(category, []).append(ticket)

    detected_incident = None
    now = datetime.utcnow()

    for category, tickets in tickets_by_category.items():
        workflow_ids = sorted({ticket.workflow_run_id for ticket in tickets})
        workflow_count = len(workflow_ids)
        if workflow_count < 3:
            continue

        incident = (
            db.query(Incident)
            .filter(
                Incident.category == category,
                Incident.status == "active",
            )
            .first()
        )
        title = _incident_title(category)
        description = (
            f"{workflow_count} {category} workflow runs were detected in the last 30 minutes. "
            f"Related workflow IDs: {', '.join(str(workflow_id) for workflow_id in workflow_ids)}."
        )
        intelligence = generate_incident_intelligence(category, tickets, replies_by_workflow)

        if incident:
            incident.title = title
            incident.description = description
            incident.severity = _severity(workflow_count)
            incident.workflow_count = workflow_count
            incident.root_cause_summary = json.dumps(intelligence["root_cause_clusters"])
            incident.operational_risks = json.dumps(intelligence["operational_risks"])
            incident.recommended_actions = json.dumps(intelligence["recommended_actions"])
            incident.last_detected_at = now
        else:
            incident = Incident(
                category=category,
                title=title,
                description=description,
                severity=_severity(workflow_count),
                workflow_count=workflow_count,
                root_cause_summary=json.dumps(intelligence["root_cause_clusters"]),
                operational_risks=json.dumps(intelligence["operational_risks"]),
                recommended_actions=json.dumps(intelligence["recommended_actions"]),
                first_detected_at=now,
                last_detected_at=now,
                status="active",
            )
            db.add(incident)

        detected_incident = incident

    return detected_incident


def related_workflow_ids_for_incident(db: Session, incident: Incident) -> list[int]:
    window_start = datetime.utcnow() - timedelta(minutes=30)
    tickets = (
        db.query(Ticket)
        .join(WorkflowRun, WorkflowRun.id == Ticket.workflow_run_id)
        .filter(
            WorkflowRun.created_at >= window_start,
            Ticket.category == incident.category,
        )
        .order_by(WorkflowRun.created_at.desc())
        .all()
    )
    return sorted({ticket.workflow_run_id for ticket in tickets}, reverse=True)
