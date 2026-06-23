import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.demo_guard import require_demo_api_key
from app.models.incident import Incident
from app.models.incident_response_plan import IncidentResponsePlan
from app.models.incident_execution_trace import IncidentExecutionTrace
from app.schemas.incident_execution_trace_schema import IncidentExecutionTraceResponse
from app.schemas.incident_response_plan_schema import IncidentResponsePlanResponse
from app.services.email_alert_service import get_alert_status
from app.services.incident_service import related_workflow_ids_for_incident
from app.services.incident_planner import create_incident_response_plan
from app.services.incident_response_executor import execute_incident_response_plan

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


def _get_or_create_response_plan(
    db: Session,
    incident: Incident,
) -> IncidentResponsePlan:
    plan = (
        db.query(IncidentResponsePlan)
        .filter(IncidentResponsePlan.incident_id == incident.id)
        .order_by(
            IncidentResponsePlan.created_at.desc(),
            IncidentResponsePlan.id.desc(),
        )
        .first()
    )
    if plan:
        return plan

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
    return plan


@router.get(
    "/{incident_id}/response-plan",
    response_model=IncidentResponsePlanResponse,
)
def get_incident_response_plan(incident_id: int, db: Session = Depends(get_db)):
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    plan = _get_or_create_response_plan(db, incident)
    return _response_plan_payload(plan)


@router.get(
    "/{incident_id}/executions",
    response_model=list[IncidentExecutionTraceResponse],
)
def get_incident_executions(incident_id: int, db: Session = Depends(get_db)):
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    return (
        db.query(IncidentExecutionTrace)
        .filter(IncidentExecutionTrace.incident_id == incident_id)
        .order_by(
            IncidentExecutionTrace.created_at.asc(),
            IncidentExecutionTrace.id.asc(),
        )
        .all()
    )


@router.post(
    "/{incident_id}/execute",
    dependencies=[Depends(require_demo_api_key)],
)
def execute_incident_plan(incident_id: int, db: Session = Depends(get_db)):
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    response_plan = _get_or_create_response_plan(db, incident)
    existing_traces = (
        db.query(IncidentExecutionTrace)
        .filter(
            IncidentExecutionTrace.incident_id == incident.id,
            IncidentExecutionTrace.response_plan_id == response_plan.id,
        )
        .order_by(
            IncidentExecutionTrace.created_at.asc(),
            IncidentExecutionTrace.id.asc(),
        )
        .all()
    )
    if existing_traces:
        results = [
            {
                "tool_name": trace.tool_name,
                "status": trace.status,
                "result_summary": trace.result_summary,
                "error_message": trace.error_message,
            }
            for trace in existing_traces
        ]
        return {
            "incident_id": incident.id,
            "response_plan_id": response_plan.id,
            "already_executed": True,
            "executed_count": sum(item["status"] == "executed" for item in results),
            "skipped_count": sum(item["status"] == "skipped" for item in results),
            "error_count": sum(item["status"] == "error" for item in results),
            "results": results,
        }

    return execute_incident_response_plan(db, incident, response_plan)
