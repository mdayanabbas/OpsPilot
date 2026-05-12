import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.incident import Incident
from app.models.incident_alert import IncidentAlert
from app.services.email_alert_service import get_alert_status
from app.services.incident_service import related_workflow_ids_for_incident

router = APIRouter()

INCIDENT_STATUSES = {"open", "investigating", "mitigated", "resolved"}


class IncidentStatusUpdate(BaseModel):
    status: str
    owner: str | None = None
    resolution_notes: str | None = None


def _json_field(value: str | None, default):
    if not value:
        return default

    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return default

    return parsed if isinstance(parsed, type(default)) else default


def _normalized_status(status: str) -> str:
    return "open" if status == "active" else status


def _serialize_alert(alert: IncidentAlert) -> dict:
    return {
        "id": alert.id,
        "alert_type": alert.alert_type,
        "severity": alert.severity,
        "recipient": alert.recipient,
        "subject": alert.subject,
        "sent_at": alert.sent_at,
    }


def _serialize_incident(db: Session, incident: Incident, include_alerts: bool = False) -> dict:
    related_workflow_ids = related_workflow_ids_for_incident(db, incident)
    payload = {
        "id": incident.id,
        "category": incident.category,
        "title": incident.title,
        "description": incident.description,
        "severity": incident.severity,
        "workflow_count": incident.workflow_count,
        "related_workflow_ids": related_workflow_ids,
        "workflow_links": [
            {"workflow_run_id": workflow_id, "href": f"/runs/{workflow_id}"}
            for workflow_id in related_workflow_ids
        ],
        "root_cause_clusters": _json_field(incident.root_cause_summary, []),
        "operational_risks": _json_field(incident.operational_risks, []),
        "recommended_actions": _json_field(incident.recommended_actions, []),
        "playbook_steps": _json_field(incident.playbook_steps, []),
        "owner": incident.owner,
        "resolution_notes": incident.resolution_notes,
        "first_detected_at": incident.first_detected_at,
        "last_detected_at": incident.last_detected_at,
        "status": _normalized_status(incident.status),
    }

    if include_alerts:
        alerts = (
            db.query(IncidentAlert)
            .filter(IncidentAlert.incident_id == incident.id)
            .order_by(IncidentAlert.sent_at.desc())
            .all()
        )
        payload["alert_history"] = [_serialize_alert(alert) for alert in alerts]
        payload["operational_timeline"] = [
            {
                "event_type": "detected",
                "label": "Incident detected",
                "timestamp": incident.first_detected_at,
            },
            *[
                {
                    "event_type": "alert",
                    "label": f"Alert sent: {alert.alert_type}",
                    "timestamp": alert.sent_at,
                }
                for alert in alerts
            ],
            {
                "event_type": "updated",
                "label": f"Current status: {_normalized_status(incident.status)}",
                "timestamp": incident.last_detected_at,
            },
        ]

    return payload


@router.get("/alerts/status")
def incident_alert_status():
    return get_alert_status()


@router.get("")
def list_incidents(db: Session = Depends(get_db)):
    incidents = (
        db.query(Incident)
        .filter(Incident.status.in_(["open", "investigating", "mitigated", "active"]))
        .order_by(Incident.last_detected_at.desc())
        .all()
    )

    return [_serialize_incident(db, incident) for incident in incidents]


@router.get("/{incident_id}")
def get_incident(incident_id: int, db: Session = Depends(get_db)):
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    return _serialize_incident(db, incident, include_alerts=True)


@router.patch("/{incident_id}/status")
def update_incident_status(
    incident_id: int,
    update: IncidentStatusUpdate,
    db: Session = Depends(get_db),
):
    status = update.status.strip().lower()
    if status not in INCIDENT_STATUSES:
        raise HTTPException(status_code=400, detail="Unsupported incident status")

    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    incident.status = status
    if update.owner is not None:
        incident.owner = update.owner.strip() or None
    if update.resolution_notes is not None:
        incident.resolution_notes = update.resolution_notes.strip() or None

    db.commit()
    db.refresh(incident)

    return _serialize_incident(db, incident, include_alerts=True)
