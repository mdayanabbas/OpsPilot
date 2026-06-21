import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.incident import Incident
from app.models.incident_response_plan import IncidentResponsePlan
from app.schemas.incident_response_plan_schema import IncidentResponsePlanResponse
from app.services.email_alert_service import get_alert_status
from app.services.incident_service import related_workflow_ids_for_incident
from app.services.incident_planner import create_incident_response_plan

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


def _response_plan_payload(plan: IncidentResponsePlan) -> dict:
    return {
        "id": plan.id,
        "incident_id": plan.incident_id,
        "plan_type": plan.plan_type,
        "next_tools": _json_field(plan.next_tools, []),
        "reasoning": plan.reasoning,
        "created_at": plan.created_at,
    }


@router.get(
    "/{incident_id}/response-plan",
    response_model=IncidentResponsePlanResponse,
)
def get_incident_response_plan(incident_id: int, db: Session = Depends(get_db)):
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    plan = (
        db.query(IncidentResponsePlan)
        .filter(IncidentResponsePlan.incident_id == incident_id)
        .order_by(
            IncidentResponsePlan.created_at.desc(),
            IncidentResponsePlan.id.desc(),
        )
        .first()
    )
    if not plan:
        intelligence = {
            "root_cause_clusters": _json_field(incident.root_cause_summary, []),
            "operational_risks": _json_field(incident.operational_risks, []),
            "recommended_actions": _json_field(incident.recommended_actions, []),
        }
        generated_plan = create_incident_response_plan(incident, intelligence)
        plan = IncidentResponsePlan(
            incident_id=incident.id,
            plan_type=generated_plan["plan_type"],
            next_tools=json.dumps(generated_plan["next_tools"]),
            reasoning=generated_plan["reasoning"],
        )
        db.add(plan)
        db.commit()
        db.refresh(plan)

    return _response_plan_payload(plan)
