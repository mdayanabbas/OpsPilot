import json

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.incident import Incident
from app.services.email_alert_service import get_alert_status
from app.services.incident_service import related_workflow_ids_for_incident

router = APIRouter()


def _json_field(value: str | None, default):
    if not value:
        return default

    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return default

    return parsed if isinstance(parsed, type(default)) else default


@router.get("/alerts/status")
def incident_alert_status():
    return get_alert_status()


@router.get("")
def list_incidents(db: Session = Depends(get_db)):
    incidents = (
        db.query(Incident)
        .filter(Incident.status == "active")
        .order_by(Incident.last_detected_at.desc())
        .all()
    )

    return [
        {
            "id": incident.id,
            "category": incident.category,
            "title": incident.title,
            "description": incident.description,
            "severity": incident.severity,
            "workflow_count": incident.workflow_count,
            "related_workflow_ids": related_workflow_ids_for_incident(db, incident),
            "root_cause_clusters": _json_field(incident.root_cause_summary, []),
            "operational_risks": _json_field(incident.operational_risks, []),
            "recommended_actions": _json_field(incident.recommended_actions, []),
            "first_detected_at": incident.first_detected_at,
            "last_detected_at": incident.last_detected_at,
            "status": incident.status,
        }
        for incident in incidents
    ]
