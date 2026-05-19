from app.agents.tools.registry import execute_tool


SAFE_TOOL_NAMES = {
    "search_memory",
    "evaluate_workflow_output",
    "generate_founder_summary",
}

TOOL_REQUIRED_CONTEXT = {
    "search_memory": ("db", "memory_category", "memory_query"),
    "evaluate_workflow_output": ("issue", "ticket", "reply"),
    "generate_founder_summary": ("issue", "ticket", "reply", "evaluation"),
}


def _tool_payload(tool_name: str, context: dict) -> dict:
    if tool_name == "search_memory":
        return {
            "db": context["db"],
            "category": context["memory_category"],
            "query": context["memory_query"],
            "limit": context.get("memory_limit", 5),
        }

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

    return {}


def _missing_context(tool_name: str, context: dict) -> list[str]:
    return [
        key
        for key in TOOL_REQUIRED_CONTEXT.get(tool_name, ())
        if key not in context or context[key] is None
    ]


def _summarize_result(result: object) -> str:
    if isinstance(result, dict):
        if "matches" in result and isinstance(result["matches"], list):
            return f"Found {len(result['matches'])} memory match(es)."
        if "summary" in result:
            return str(result["summary"])[:500]
        if "quality_score" in result:
            return f"Evaluation quality score: {result.get('quality_score')}"
        return ", ".join(sorted(result.keys()))[:500]

    return str(result)[:500]


def execute_planned_tools(planner_decision: dict, context: dict) -> dict:
    planner_decision = planner_decision if isinstance(planner_decision, dict) else {}
    context = context if isinstance(context, dict) else {}
    results = []
    errors = []

    for planned_tool in planner_decision.get("next_tools", []):
        tool_name = planned_tool.get("tool_name") if isinstance(planned_tool, dict) else None
        if not tool_name:
            continue

        if tool_name not in SAFE_TOOL_NAMES:
            results.append(
                {
                    "tool_name": tool_name,
                    "status": "skipped",
                    "result_summary": "Tool is not allowlisted for dynamic execution v1.",
                    "error_message": None,
                }
            )
            continue

        missing = _missing_context(tool_name, context)
        if missing:
            results.append(
                {
                    "tool_name": tool_name,
                    "status": "skipped",
                    "result_summary": f"Missing context: {', '.join(missing)}.",
                    "error_message": None,
                }
            )
            continue

        execution_result = execute_tool(tool_name, _tool_payload(tool_name, context))
        if execution_result.get("ok"):
            results.append(
                {
                    "tool_name": tool_name,
                    "status": "executed",
                    "result_summary": _summarize_result(execution_result.get("result")),
                    "error_message": None,
                }
            )
        else:
            error = execution_result.get("error", {})
            error_message = error.get("message") or "Tool execution failed."
            results.append(
                {
                    "tool_name": tool_name,
                    "status": "error",
                    "result_summary": "",
                    "error_message": error_message,
                }
            )
            errors.append({"tool_name": tool_name, "error_message": error_message})

    return {
        "executed_count": len([result for result in results if result["status"] == "executed"]),
        "skipped_count": len([result for result in results if result["status"] == "skipped"]),
        "error_count": len(errors),
        "results": results,
        "errors": errors,
    }
