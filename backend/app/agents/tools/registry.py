from dataclasses import dataclass
from typing import Any, Callable

from sqlalchemy.orm import Session

from app.agents.nodes.evaluation_node import evaluate_workflow_output
from app.agents.nodes.founder_summary_node import generate_founder_summary
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


def _serialize_memory_item(item) -> dict:
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


def _search_memory_handler(payload: dict) -> dict:
    matches = search_memory(
        db=_required_db(payload),
        category=_required(payload, "category"),
        query=_required(payload, "query"),
        limit=payload.get("limit", 5),
    )
    return {"matches": [_serialize_memory_item(item) for item in matches]}


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
