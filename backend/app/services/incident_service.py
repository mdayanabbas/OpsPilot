from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models.incident import Incident
from app.models.ticket import Ticket
from app.models.workflow import WorkflowRun


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

        if incident:
            incident.title = title
            incident.description = description
            incident.severity = _severity(workflow_count)
            incident.workflow_count = workflow_count
            incident.last_detected_at = now
        else:
            incident = Incident(
                category=category,
                title=title,
                description=description,
                severity=_severity(workflow_count),
                workflow_count=workflow_count,
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
