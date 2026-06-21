"""Explicit, read-only execution for persisted incident response plans."""

import json

from app.agents.tools.registry import execute_tool
from app.models.incident_execution_trace import IncidentExecutionTrace


INCIDENT_TOOL_ALLOWLIST = {"search_memory", "generate_founder_summary"}


def _planned_tools(response_plan) -> list:
    tools = getattr(response_plan, "next_tools", [])
    if isinstance(tools, str):
        try:
            tools = json.loads(tools)
        except (TypeError, json.JSONDecodeError):
            return []
    return tools if isinstance(tools, list) else []


def _incident_context(incident) -> dict:
    priority = "high" if incident.severity in {"high", "critical"} else "medium"
    issue = {
        "title": incident.title,
        "category": incident.category,
        "severity": priority,
        "customer": None,
        "description": incident.description,
    }
    return {
        "issue": issue,
        "ticket": {
            "title": incident.title,
            "priority": priority,
            "category": incident.category,
            "description": incident.description,
            "requires_approval": True,
        },
        "reply": {
            "customer": None,
            "issue": incident.description,
            "draft_reply": None,
            "risk_level": "high" if incident.severity == "critical" else "medium",
            "risk_reason": "Incident response output requires human review.",
            "requires_approval": True,
            "fallback_used": False,
        },
        "evaluation": {
            "requires_human_review": True,
            "risks": "Incident response plan is advisory and requires human review.",
        },
        "memory_matches": [],
    }


def _payload(tool_name: str, db, incident, context: dict) -> dict:
    if tool_name == "search_memory":
        return {
            "db": db,
            "category": incident.category,
            "query": f"{incident.title} {incident.description} {incident.severity}",
            "limit": 5,
        }
    return {
        "issue": context["issue"],
        "ticket": context["ticket"],
        "reply": context["reply"],
        "evaluation": context["evaluation"],
        "memory_matches": context["memory_matches"],
        "tool_calls": [],
    }


def _summary(tool_name: str, result) -> str:
    if not isinstance(result, dict):
        return str(result)[:500]
    if tool_name == "search_memory":
        return f"Found {len(result.get('matches', []))} related memory item(s)."
    if tool_name == "generate_founder_summary":
        return str(result.get("summary") or "Founder summary generated.")[:500]
    return ", ".join(sorted(result.keys()))[:500]


def execute_incident_response_plan(db, incident, response_plan) -> dict:
    results = []
    context = _incident_context(incident)

    for planned_tool in _planned_tools(response_plan):
        tool_name = (
            planned_tool.get("tool_name")
            if isinstance(planned_tool, dict)
            else planned_tool
        )
        tool_name = tool_name if isinstance(tool_name, str) and tool_name else "unknown"

        if tool_name not in INCIDENT_TOOL_ALLOWLIST:
            trace_result = {
                "tool_name": tool_name,
                "status": "skipped",
                "result_summary": "Tool is not allowlisted for read-only incident execution v1.",
                "error_message": None,
            }
        else:
            try:
                execution = execute_tool(
                    tool_name,
                    _payload(tool_name, db, incident, context),
                )
                if execution.get("ok"):
                    raw_result = execution.get("result")
                    if tool_name == "search_memory" and isinstance(raw_result, dict):
                        context["memory_matches"] = raw_result.get("matches", [])
                    trace_result = {
                        "tool_name": tool_name,
                        "status": "executed",
                        "result_summary": _summary(tool_name, raw_result),
                        "error_message": None,
                    }
                else:
                    error = execution.get("error") or {}
                    trace_result = {
                        "tool_name": tool_name,
                        "status": "error",
                        "result_summary": "",
                        "error_message": error.get("message") or "Tool execution failed.",
                    }
            except Exception as exc:
                trace_result = {
                    "tool_name": tool_name,
                    "status": "error",
                    "result_summary": "",
                    "error_message": str(exc),
                }

        db.add(
            IncidentExecutionTrace(
                incident_id=incident.id,
                response_plan_id=response_plan.id,
                **trace_result,
            )
        )
        results.append(trace_result)

    db.commit()
    return {
        "incident_id": incident.id,
        "response_plan_id": response_plan.id,
        "executed_count": sum(item["status"] == "executed" for item in results),
        "skipped_count": sum(item["status"] == "skipped" for item in results),
        "error_count": sum(item["status"] == "error" for item in results),
        "results": results,
    }
