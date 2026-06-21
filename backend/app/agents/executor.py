"""Dynamic execution for planner-selected tools with durable traces."""

import json

from app.agents.tools.registry import execute_tool
from app.models.agent_execution_trace import AgentExecutionTrace


SAFE_TOOL_NAMES = {
    "search_memory",
    "generate_ticket",
    "generate_customer_reply",
    "evaluate_workflow_output",
    "generate_founder_summary",
    "detect_incident",
}

TOOL_REQUIRED_CONTEXT = {
    "search_memory": ("memory_category", "memory_query"),
    "generate_ticket": ("issue",),
    "generate_customer_reply": ("issue",),
    "evaluate_workflow_output": ("issue", "ticket", "reply"),
    "generate_founder_summary": ("issue", "ticket", "reply", "evaluation"),
    "detect_incident": (),
}


def _planner_value(planner_decision, key: str, default=None):
    if isinstance(planner_decision, dict):
        return planner_decision.get(key, default)
    return getattr(planner_decision, key, default)


def _planned_tools(planner_decision) -> list:
    next_tools = _planner_value(planner_decision, "next_tools", [])
    if isinstance(next_tools, str):
        try:
            next_tools = json.loads(next_tools)
        except (TypeError, json.JSONDecodeError):
            return []
    return next_tools if isinstance(next_tools, list) else []


def _tool_payload(tool_name: str, db, context: dict) -> dict:
    if tool_name == "search_memory":
        return {
            "db": db,
            "category": context["memory_category"],
            "query": context["memory_query"],
            "limit": context.get("memory_limit", 5),
        }
    if tool_name in {"generate_ticket", "generate_customer_reply"}:
        return {"issue": context["issue"]}
    if tool_name == "evaluate_workflow_output":
        return {
            "issue": context["issue"],
            "ticket": context["ticket"],
            "reply": context["reply"],
            "fallback_used": context.get("fallback_used", False),
        }
    if tool_name == "generate_founder_summary":
        return {
            "issue": context["issue"],
            "ticket": context["ticket"],
            "reply": context["reply"],
            "evaluation": context["evaluation"],
            "tool_calls": context.get("tool_calls"),
            "memory_matches": context.get("memory_matches"),
        }
    if tool_name == "detect_incident":
        return {"db": db}
    return {}


def _missing_context(tool_name: str, context: dict) -> list[str]:
    return [
        key
        for key in TOOL_REQUIRED_CONTEXT.get(tool_name, ())
        if key not in context or context[key] is None
    ]


def _summarize_result(result: object) -> str:
    if isinstance(result, dict):
        if isinstance(result.get("matches"), list):
            return f"Found {len(result['matches'])} memory match(es)."
        if "summary" in result:
            return str(result["summary"])[:500]
        if "quality_score" in result:
            return f"Evaluation quality score: {result.get('quality_score')}"
        if "incident" in result:
            return "Incident detected." if result["incident"] else "No active incident detected."
        return ", ".join(sorted(result.keys()))[:500]
    return str(result)[:500]


def _update_context(tool_name: str, result: object, context: dict) -> None:
    if not isinstance(result, dict):
        return
    if tool_name == "search_memory":
        context["memory_matches"] = result.get("matches", [])
    elif tool_name == "generate_ticket":
        context["ticket"] = result
        print("[tool_executor] dynamic ticket generated")
    elif tool_name == "generate_customer_reply":
        context["reply"] = result
        print("[tool_executor] dynamic reply generated")
    elif tool_name == "evaluate_workflow_output":
        context["evaluation"] = result
    elif tool_name == "generate_founder_summary":
        context["founder_summary"] = result
    elif tool_name == "detect_incident":
        context["incident"] = result.get("incident")


def execute_planned_tools(
    db,
    workflow_run_id: int,
    planner_decision,
    context: dict,
) -> dict:
    print("[tool_executor] entered")
    print(f"[tool_executor] workflow_run_id={workflow_run_id}")

    context = context if isinstance(context, dict) else {}
    planner_tools = _planned_tools(planner_decision)
    planner_decision_id = _planner_value(planner_decision, "id")
    print(f"[tool_executor] planner_tools_count={len(planner_tools)}")

    results = []
    for planned_tool in planner_tools:
        tool_name = (
            planned_tool.get("tool_name")
            if isinstance(planned_tool, dict)
            else planned_tool
        )
        if not isinstance(tool_name, str) or not tool_name:
            tool_name = "unknown"

        print(f"[tool_executor] executing tool={tool_name}")
        try:
            if tool_name not in SAFE_TOOL_NAMES:
                trace_result = {
                    "tool_name": tool_name,
                    "status": "skipped",
                    "result_summary": "Tool is not allowlisted for dynamic execution v2.",
                    "error_message": None,
                }
            else:
                missing = _missing_context(tool_name, context)
                if missing:
                    trace_result = {
                        "tool_name": tool_name,
                        "status": "skipped",
                        "result_summary": f"Missing context: {', '.join(missing)}.",
                        "error_message": None,
                    }
                else:
                    execution = execute_tool(
                        tool_name,
                        _tool_payload(tool_name, db, context),
                    )
                    if execution.get("ok"):
                        raw_result = execution.get("result")
                        _update_context(tool_name, raw_result, context)
                        if tool_name == "generate_ticket":
                            result_summary = (
                                f"Generated ticket title={raw_result.get('title', 'unknown')}"
                                if isinstance(raw_result, dict)
                                else "Generated ticket."
                            )
                        elif tool_name == "generate_customer_reply":
                            result_summary = (
                                f"Generated reply risk_level={raw_result.get('risk_level', 'unknown')}"
                                if isinstance(raw_result, dict)
                                else "Generated customer reply."
                            )
                        else:
                            result_summary = _summarize_result(raw_result)
                        trace_result = {
                            "tool_name": tool_name,
                            "status": "executed",
                            "result_summary": result_summary,
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

        print(f"[tool_executor] saving trace tool={tool_name}")
        db.add(
            AgentExecutionTrace(
                workflow_run_id=workflow_run_id,
                planner_decision_id=planner_decision_id,
                **trace_result,
            )
        )
        results.append(trace_result)

    db.commit()
    print("[tool_executor] completed")

    return {
        "executed_count": sum(item["status"] == "executed" for item in results),
        "skipped_count": sum(item["status"] == "skipped" for item in results),
        "error_count": sum(item["status"] == "error" for item in results),
        "results": results,
    }
