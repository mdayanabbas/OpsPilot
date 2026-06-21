from dataclasses import dataclass
from typing import Any, Callable

from sqlalchemy.orm import Session

from app.agents.nodes.evaluation_node import evaluate_workflow_output
from app.agents.nodes.founder_summary_node import generate_founder_summary
from app.agents.nodes.reply_generation_node import generate_customer_reply
from app.agents.nodes.ticket_generation_node import generate_ticket
from app.models.incident import Incident
from app.models.memory import MemoryItem
from app.services.email_alert_service import send_incident_alert
from app.services.incident_service import detect_incidents
from app.services.memory_service import search_memory


ToolHandler = Callable[[dict], dict]


@dataclass(frozen=True)
class AgentTool:
    name: str
    description: str
    input_schema: dict
    handler: ToolHandler


def _required(payload: dict, key: str) -> Any:
    if key not in payload:
        raise ValueError(f"Missing required payload field: {key}")
    return payload[key]


def _required_db(payload: dict) -> Session:
    db = _required(payload, "db")
    if not isinstance(db, Session):
        raise ValueError("Payload field 'db' must be a SQLAlchemy Session")
    return db


def _serialize_memory_item(item: MemoryItem) -> dict:
    return {
        "id": item.id,
        "workflow_run_id": item.workflow_run_id,
        "item_type": item.item_type,
        "title": item.title,
        "category": item.category,
        "content": item.content,
        "relevance_score": getattr(item, "relevance_score", None),
        "created_at": item.created_at.isoformat() if item.created_at else None,
    }


def _serialize_incident(incident: Incident | None) -> dict | None:
    if incident is None:
        return None

    return {
        "id": incident.id,
        "category": incident.category,
        "title": incident.title,
        "description": incident.description,
        "severity": incident.severity,
        "workflow_count": incident.workflow_count,
        "root_cause_summary": incident.root_cause_summary,
        "operational_risks": incident.operational_risks,
        "recommended_actions": incident.recommended_actions,
        "first_detected_at": (
            incident.first_detected_at.isoformat()
            if incident.first_detected_at
            else None
        ),
        "last_detected_at": (
            incident.last_detected_at.isoformat()
            if incident.last_detected_at
            else None
        ),
        "status": incident.status,
    }


def _search_memory_handler(payload: dict) -> dict:
    matches = search_memory(
        db=_required_db(payload),
        category=_required(payload, "category"),
        query=_required(payload, "query"),
        limit=payload.get("limit", 5),
    )
    return {"matches": [_serialize_memory_item(item) for item in matches]}


def _generate_ticket_handler(payload: dict) -> dict:
    return generate_ticket(_required(payload, "issue"))


def _generate_customer_reply_handler(payload: dict) -> dict:
    return generate_customer_reply(_required(payload, "issue"))


def _evaluate_workflow_output_handler(payload: dict) -> dict:
    return evaluate_workflow_output(
        issue=_required(payload, "issue"),
        ticket=_required(payload, "ticket"),
        reply=_required(payload, "reply"),
        fallback_used=payload.get("fallback_used", False),
    )


def _generate_founder_summary_handler(payload: dict) -> dict:
    return generate_founder_summary(
        issue=_required(payload, "issue"),
        ticket=_required(payload, "ticket"),
        reply=_required(payload, "reply"),
        evaluation=_required(payload, "evaluation"),
        tool_calls=payload.get("tool_calls"),
        memory_matches=payload.get("memory_matches"),
    )


def _detect_incident_handler(payload: dict) -> dict:
    incident = detect_incidents(_required_db(payload))
    return {"incident": _serialize_incident(incident)}


def _send_incident_alert_handler(payload: dict) -> dict:
    sent = send_incident_alert(
        incident=_required(payload, "incident"),
        intelligence=_required(payload, "intelligence"),
        related_workflow_ids=_required(payload, "related_workflow_ids"),
        reason=_required(payload, "reason"),
    )
    return {"sent": sent}


_TOOL_REGISTRY: dict[str, AgentTool] = {
    "search_memory": AgentTool(
        name="search_memory",
        description="Search stored workflow memory for similar past issues.",
        input_schema={
            "type": "object",
            "required": ["db", "category", "query"],
            "properties": {
                "db": {"description": "SQLAlchemy Session"},
                "category": {"type": "string"},
                "query": {"type": "string"},
                "limit": {"type": "integer", "default": 5},
            },
        },
        handler=_search_memory_handler,
    ),
    "generate_ticket": AgentTool(
        name="generate_ticket",
        description="Generate an engineering ticket from an extracted issue.",
        input_schema={
            "type": "object",
            "properties": {"issue": {"type": "object"}},
            "required": ["issue"],
        },
        handler=_generate_ticket_handler,
    ),
    "generate_customer_reply": AgentTool(
        name="generate_customer_reply",
        description="Generate a safe draft customer reply for an issue.",
        input_schema={
            "type": "object",
            "properties": {"issue": {"type": "object"}},
            "required": ["issue"],
        },
        handler=_generate_customer_reply_handler,
    ),
    "evaluate_workflow_output": AgentTool(
        name="evaluate_workflow_output",
        description="Evaluate generated ticket and reply quality for a workflow.",
        input_schema={
            "type": "object",
            "required": ["issue", "ticket", "reply"],
            "properties": {
                "issue": {"type": "object"},
                "ticket": {"type": "object"},
                "reply": {"type": "object"},
                "fallback_used": {"type": "boolean", "default": False},
            },
            "required": ["issue", "ticket", "reply"],
        },
        handler=_evaluate_workflow_output_handler,
    ),
    "generate_founder_summary": AgentTool(
        name="generate_founder_summary",
        description="Generate a founder-facing workflow summary and recommended actions.",
        input_schema={
            "type": "object",
            "required": ["issue", "ticket", "reply", "evaluation"],
            "properties": {
                "issue": {"type": "object"},
                "ticket": {"type": "object"},
                "reply": {"type": "object"},
                "evaluation": {"type": "object"},
                "tool_calls": {"type": "array", "items": {"type": "object"}},
                "memory_matches": {"type": "array", "items": {"type": "object"}},
            },
        },
        handler=_generate_founder_summary_handler,
    ),
    "detect_incident": AgentTool(
        name="detect_incident",
        description="Detect active incident clusters from recent workflow activity.",
        input_schema={
            "type": "object",
            "properties": {"db": {"description": "SQLAlchemy Session"}},
            "required": ["db"],
        },
        handler=_detect_incident_handler,
    ),
    "send_incident_alert": AgentTool(
        name="send_incident_alert",
        description="Send an internal alert for a detected incident.",
        input_schema={
            "type": "object",
            "properties": {
                "incident": {"description": "Incident model instance"},
                "intelligence": {"type": "object"},
                "related_workflow_ids": {
                    "type": "array",
                    "items": {"type": "integer"},
                },
                "reason": {"type": "string"},
            },
            "required": [
                "incident",
                "intelligence",
                "related_workflow_ids",
                "reason",
            ],
        },
        handler=_send_incident_alert_handler,
    ),
}


def get_tool_registry() -> dict:
    return dict(_TOOL_REGISTRY)


def list_tools() -> list[dict]:
    return [
        {
            "name": tool.name,
            "description": tool.description,
            "input_schema": tool.input_schema,
        }
        for tool in _TOOL_REGISTRY.values()
    ]


def execute_tool(tool_name: str, payload: dict) -> dict:
    tool = _TOOL_REGISTRY.get(tool_name)
    registry = get_tool_registry()
    tool = registry.get(tool_name)
    if tool is None:
        raise ValueError(f"Unknown tool: {tool_name}")

    try:
        result = tool.handler(payload)
    except Exception as exc:
        return {
            "ok": False,
            "tool_name": tool_name,
            "error": {
                "type": exc.__class__.__name__,
                "message": str(exc),
            },
        }

    return {
        "ok": True,
        "tool_name": tool_name,
        "result": result,
    }
