from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.incident import Incident
from app.services.incident_service import related_workflow_ids_for_incident

router = APIRouter()


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
            "first_detected_at": incident.first_detected_at,
            "last_detected_at": incident.last_detected_at,
            "status": incident.status,
        }
        for incident in incidents
    ]
