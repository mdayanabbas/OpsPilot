import json
import re

from app.config import LLM_PROVIDER
from app.services.gemini_service import GeminiServiceError, generate_json


SENSITIVE_CATEGORIES = {"billing", "auth", "refund", "security"}
UNKNOWN_CATEGORIES = {"", "unknown", "other", "uncategorized", "unclear"}
EXTREMELY_LOW_CONFIDENCE = 0.25
MIN_VAGUE_TEXT_LENGTH = 18

ACTIONABLE_INDICATORS = {
    "billing": (
        "payment successful",
        "subscription inactive",
        "subscription not active",
        "charged",
        "invoice",
        "refund",
        "payment pending",
        "duplicate charge",
    ),
    "auth": (
        "login failed",
        "session expired",
        "password reset",
        "cannot access account",
    ),
    "performance": (
        "slow",
        "freeze",
        "freezing",
        "timeout",
        "crash",
    ),
}

ALLOWED_PLAN_TYPES = {
    "standard_triage",
    "clarification",
    "human_review",
    "incident_response",
}

ALLOWED_TOOLS = {
    "search_memory",
    "generate_ticket",
    "generate_customer_reply",
    "evaluate_workflow_output",
    "generate_founder_summary",
    "detect_incident",
}

TOOL_DETAILS = {
    "search_memory": {
        "reason": "Find related past workflows that may inform priority and response.",
        "priority": "high",
    },
    "generate_ticket": {
        "reason": "Create an engineering ticket for the actionable customer issue.",
        "priority": "high",
    },
    "generate_customer_reply": {
        "reason": "Draft a safe customer reply for review.",
        "priority": "high",
    },
    "evaluate_workflow_output": {
        "reason": "Evaluate ticket and reply quality before downstream summary.",
        "priority": "medium",
    },
    "generate_founder_summary": {
        "reason": "Summarize workflow outcome, risks, and recommended next actions.",
        "priority": "medium",
    },
    "detect_incident": {
        "reason": "Re-check incident signals before any human-led response.",
        "priority": "high",
    },
}

STANDARD_TRIAGE_TOOLS = [
    "generate_ticket",
    "generate_customer_reply",
    "evaluate_workflow_output",
    "generate_founder_summary",
]

INCIDENT_RESPONSE_TOOLS = [
    "detect_incident",
    "search_memory",
    "generate_founder_summary",
]

PLANNER_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "plan_type": {"type": "string"},
        "next_tools": {
            "type": "array",
            "items": {"type": "string"},
        },
        "reasoning": {"type": "string"},
        "requires_human_approval": {"type": "boolean"},
    },
    "required": [
        "plan_type",
        "next_tools",
        "reasoning",
        "requires_human_approval",
    ],
}


class PlannerValidationError(ValueError):
    """Raised when an LLM planner response fails deterministic validation."""


class PlannerParseError(ValueError):
    """Raised when the planner cannot parse an LLM response into a JSON object."""


def _issue_category(context: dict) -> str:
    issue = context.get("issue")
    if not isinstance(issue, dict):
        return ""

    category = issue.get("category")
    return category.strip().lower() if isinstance(category, str) else ""


def _issue_text(context: dict) -> str:
    issue = context.get("issue")
    values = []

    if isinstance(issue, dict):
        values.extend(
            value
            for value in (
                issue.get("title"),
                issue.get("description"),
                issue.get("summary"),
                issue.get("customer"),
            )
            if isinstance(value, str)
        )

    customer_impact = context.get("customer_impact")
    if isinstance(customer_impact, str):
        values.append(customer_impact)

    return " ".join(values).strip().lower()


def _indicator_matches(text: str, indicator: str) -> bool:
    if indicator == "freeze":
        return bool(re.search(r"\bfreez(?:e|es|ing)\b", text))

    if indicator == "crash":
        return bool(re.search(r"\bcrash(?:es|ed|ing)?\b", text))

    return indicator in text


def _actionable_indicator_categories(context: dict) -> set[str]:
    text = _issue_text(context)
    if not text:
        return set()

    return {
        category
        for category, indicators in ACTIONABLE_INDICATORS.items()
        if any(_indicator_matches(text, indicator) for indicator in indicators)
    }


def _has_actionable_indicators(context: dict) -> bool:
    return bool(_actionable_indicator_categories(context))


def _has_actionable_issue(context: dict) -> bool:
    issue = context.get("issue")
    if not isinstance(issue, dict):
        return False

    category = _issue_category(context)
    title = issue.get("title")
    description = issue.get("description")

    has_category = category not in UNKNOWN_CATEGORIES
    has_text = any(
        isinstance(value, str) and value.strip()
        for value in (title, description)
    )

    return has_text and (has_category or _has_actionable_indicators(context))


def _title_or_description_too_vague(context: dict) -> bool:
    issue = context.get("issue")
    if not isinstance(issue, dict):
        return True

    text = " ".join(
        value.strip()
        for value in (issue.get("title"), issue.get("description"))
        if isinstance(value, str) and value.strip()
    )
    if len(text) < MIN_VAGUE_TEXT_LENGTH:
        return True

    vague_phrases = {
        "help",
        "issue",
        "problem",
        "not working",
        "customer issue",
        "something broke",
    }
    return text.strip().lower() in vague_phrases


def _confidence_extremely_low(context: dict) -> bool:
    try:
        confidence = float(context.get("confidence", 1.0))
    except (TypeError, ValueError):
        return False

    return confidence < EXTREMELY_LOW_CONFIDENCE


def _should_clarify(context: dict, *, log_rejection: bool = True) -> bool:
    if _has_actionable_indicators(context):
        if log_rejection and context.get("requires_clarification") is True:
            print("[planner] clarification rejected due to actionable indicators")
        return False

    category_unknown = _issue_category(context) in UNKNOWN_CATEGORIES
    no_actionable_issue = not _has_actionable_issue(context)
    vague_issue = _title_or_description_too_vague(context)
    extremely_low_confidence = _confidence_extremely_low(context)

    if _has_actionable_issue(context) and not vague_issue and not extremely_low_confidence:
        return False

    return (
        context.get("requires_clarification") is True
        or no_actionable_issue
        or category_unknown
        or vague_issue
        or extremely_low_confidence
    )


def _has_memory_matches(context: dict) -> bool:
    memory_matches = context.get("memory_matches")
    return isinstance(memory_matches, list) and bool(memory_matches)


def _requires_human_approval(context: dict) -> bool:
    category = _issue_category(context)
    indicator_categories = _actionable_indicator_categories(context)
    if category in SENSITIVE_CATEGORIES or indicator_categories.intersection(SENSITIVE_CATEGORIES):
        return True

    evaluation = context.get("evaluation")
    if isinstance(evaluation, dict) and evaluation.get("requires_human_review") is True:
        return True

    reply = context.get("reply")
    if isinstance(reply, dict) and reply.get("requires_approval") is True:
        return True

    return False


def _tool_entry(tool_name: str) -> dict:
    details = TOOL_DETAILS[tool_name]
    return {
        "tool_name": tool_name,
        "reason": details["reason"],
        "priority": details["priority"],
    }


def _planner_selected_tool_entry(tool_name: str) -> dict:
    return {
        "tool_name": tool_name,
        "reason": "Selected by planner",
        "priority": "medium",
    }


def _tool_entries(tool_names: list[str]) -> list[dict]:
    return [_tool_entry(tool_name) for tool_name in tool_names]


def _reasoning_summary(
    plan_type: str,
    context: dict,
    requires_human_approval: bool,
) -> str:
    parts = []

    if plan_type == "clarification":
        parts.append("Clarification is required before running tools.")
    elif plan_type == "incident_response":
        parts.append("Incident response selected because incident signals were detected.")
    elif plan_type == "human_review":
        parts.append("Human review selected because the workflow requires approval.")
    else:
        parts.append("Standard triage selected for an actionable workflow issue.")

    category = _issue_category(context)
    if category in SENSITIVE_CATEGORIES:
        parts.append(f"Category '{category}' requires human approval.")
    elif requires_human_approval:
        parts.append("Existing workflow outputs indicate human approval is required.")

    if _has_memory_matches(context):
        parts.append(
            "Memory matches are present and should inform prioritization and summary."
        )

    if context.get("fallback_used") is True:
        parts.append("Fallback execution was used, so outputs should be reviewed carefully.")

    return " ".join(parts)


def _deterministic_plan(context: dict, *, used_fallback: bool = False) -> dict:
    requires_human_approval = _requires_human_approval(context)

    if _should_clarify(context):
        plan_type = "clarification"
        next_tools = []
    elif context.get("incident_detected") is True:
        plan_type = "incident_response"
        next_tools = INCIDENT_RESPONSE_TOOLS
        requires_human_approval = True
    elif requires_human_approval:
        plan_type = "human_review"
        next_tools = STANDARD_TRIAGE_TOOLS
    else:
        plan_type = "standard_triage"
        next_tools = STANDARD_TRIAGE_TOOLS

    return {
        "plan_type": plan_type,
        "next_tools": _tool_entries(next_tools),
        "requires_human_approval": requires_human_approval,
        "reasoning_summary": _reasoning_summary(
            plan_type=plan_type,
            context=context,
            requires_human_approval=requires_human_approval,
        ),
        "planner_provider": "deterministic",
        "used_fallback": used_fallback,
        "raw_reasoning": "",
    }


def _compact_context(context: dict) -> dict:
    return {
        "workflow_type": context.get("workflow_type"),
        "issue": context.get("issue"),
        "memory_matches": context.get("memory_matches", []),
        "evaluation": context.get("evaluation"),
        "incident_detected": context.get("incident_detected"),
        "incident_signals": context.get("incident_signals"),
        "customer_impact": context.get("customer_impact"),
        "confidence": context.get("confidence"),
        "requires_clarification": context.get("requires_clarification"),
        "fallback_used": context.get("fallback_used"),
    }


def _planner_prompt(context: dict) -> str:
    compact_context = json.dumps(_compact_context(context), default=str, indent=2)
    allowed_plan_types = ", ".join(sorted(ALLOWED_PLAN_TYPES))
    allowed_tools = ", ".join(sorted(ALLOWED_TOOLS))

    return f"""
You are the hybrid planner for OpsPilot.

Return exactly one JSON object and nothing else. Do not use markdown. Do not use
code fences. Do not include any explanation outside the JSON object.

Analyze the workflow context and choose the next safe plan. Consider:
- issue category
- memory matches
- evaluation output
- incident signals
- customer impact
- workflow confidence

Allowed plan_type values: {allowed_plan_types}
Allowed next_tools values: {allowed_tools}

Return JSON only in this exact shape:
{{
  "plan_type": "standard_triage | clarification | human_review | incident_response",
  "next_tools": ["tool_name"],
  "reasoning": "brief planning rationale",
  "requires_human_approval": false
}}

Do not plan autonomous side effects. Do not invent tools. Prefer human_review for
sensitive categories, low confidence, unclear customer impact, or provider fallback risk.

Workflow context:
{compact_context}
""".strip()


def generate_llm_plan(context: dict) -> dict:
    context = context if isinstance(context, dict) else {}
    selected_provider = LLM_PROVIDER if LLM_PROVIDER in {"gemini", "local", "auto"} else "local"
    print(f"[planner] selected provider={selected_provider}")

    raw_response = generate_json(_planner_prompt(context), PLANNER_RESPONSE_SCHEMA)
    print(f"[planner] raw LLM planner response={raw_response!r}")

    parsed_plan = _parse_planner_response(raw_response)
    print("[planner] llm plan generated")
    return parsed_plan


def _strip_code_fence(text: str) -> str:
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped

    lines = stripped.splitlines()
    if lines and lines[0].strip().startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()


def _find_first_json_object(text: str) -> str:
    start_positions = [index for index, char in enumerate(text) if char == "{"]
    for start in start_positions:
        depth = 0
        in_string = False
        escape = False

        for index in range(start, len(text)):
            char = text[index]

            if in_string:
                if escape:
                    escape = False
                elif char == "\\":
                    escape = True
                elif char == '"':
                    in_string = False
                continue

            if char == '"':
                in_string = True
            elif char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    candidate = text[start : index + 1]
                    try:
                        json.loads(candidate)
                    except json.JSONDecodeError as exc:
                        print(f"[planner] JSON parse error={exc}")
                        break
                    return candidate

    raise PlannerParseError("No valid JSON object found in LLM planner response.")


def _parse_json_text(text: str) -> dict:
    stripped = _strip_code_fence(text)

    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError as exc:
        print(f"[planner] JSON parse error={exc}")
    else:
        if isinstance(parsed, str):
            return _parse_json_text(parsed)
        if isinstance(parsed, dict):
            return parsed
        raise PlannerParseError("LLM planner JSON response must be an object.")

    candidate = _find_first_json_object(stripped)
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError as exc:
        print(f"[planner] JSON parse error={exc}")
        raise PlannerParseError(f"Invalid planner JSON object: {exc}") from exc

    if isinstance(parsed, str):
        return _parse_json_text(parsed)
    if not isinstance(parsed, dict):
        raise PlannerParseError("LLM planner JSON response must be an object.")

    return parsed


def _parse_planner_response(raw_response: object) -> dict:
    if isinstance(raw_response, dict):
        return raw_response

    if isinstance(raw_response, str):
        return _parse_json_text(raw_response)

    raise PlannerParseError("LLM planner response must be a JSON object or string.")


def _validate_llm_plan(raw_plan: dict, context: dict) -> dict:
    if not isinstance(raw_plan, dict):
        raise PlannerValidationError("Planner response must be an object.")

    plan_type = raw_plan.get("plan_type")
    if plan_type not in ALLOWED_PLAN_TYPES:
        raise PlannerValidationError("Planner returned an invalid plan_type.")

    raw_tools = raw_plan.get("next_tools")
    if not isinstance(raw_tools, list):
        raise PlannerValidationError("Planner next_tools must be a list.")

    next_tools = []
    for raw_tool in raw_tools:
        if isinstance(raw_tool, str):
            tool_name = raw_tool
            repaired_tool = _planner_selected_tool_entry(tool_name)
        elif isinstance(raw_tool, dict):
            tool_name = raw_tool.get("tool_name")
            repaired_tool = {
                "tool_name": tool_name,
                "reason": raw_tool.get("reason") or "Selected by planner",
                "priority": raw_tool.get("priority") or "medium",
            }
        else:
            raise PlannerValidationError("Planner returned a malformed tool entry.")

        if tool_name not in ALLOWED_TOOLS:
            raise PlannerValidationError(f"Planner returned an unknown tool: {tool_name!r}.")
        next_tools.append(repaired_tool)

    if plan_type == "clarification" and next_tools:
        raise PlannerValidationError("Clarification plans cannot run tools.")

    if plan_type == "clarification" and _has_actionable_indicators(context):
        print("[planner] clarification rejected due to actionable indicators")
        raise PlannerValidationError("Planner requested clarification for an actionable issue.")

    if _should_clarify(context, log_rejection=False) and plan_type != "clarification":
        raise PlannerValidationError("Planner ignored required clarification.")

    if context.get("incident_detected") is True and plan_type != "incident_response":
        raise PlannerValidationError("Planner ignored incident signals.")

    deterministic_requires_approval = _requires_human_approval(context)
    requires_human_approval = raw_plan.get("requires_human_approval")
    if not isinstance(requires_human_approval, bool):
        raise PlannerValidationError("requires_human_approval must be boolean.")

    if deterministic_requires_approval and not requires_human_approval:
        raise PlannerValidationError("Planner bypassed required human approval.")

    reasoning = raw_plan.get("reasoning")
    if not isinstance(reasoning, str) or not reasoning.strip():
        raise PlannerValidationError("Planner reasoning must be a non-empty string.")

    provider = raw_plan.get("provider")
    if provider not in {"gemini", "local", "fallback"}:
        provider = "gemini"

    used_provider_fallback = bool(raw_plan.get("fallback_used")) or provider == "fallback"

    print("[planner] validation passed")
    return {
        "plan_type": plan_type,
        "next_tools": next_tools,
        "requires_human_approval": requires_human_approval,
        "reasoning_summary": reasoning.strip(),
        "planner_provider": provider,
        "used_fallback": used_provider_fallback,
        "raw_reasoning": reasoning.strip(),
    }


def plan_next_actions(context: dict) -> dict:
    context = context if isinstance(context, dict) else {}

    try:
        raw_plan = generate_llm_plan(context)
        return _validate_llm_plan(raw_plan, context)
    except (GeminiServiceError, PlannerParseError, PlannerValidationError, ValueError, TypeError) as exc:
        if isinstance(exc, PlannerValidationError):
            print(f"[planner] validation failure reason={exc}")
        print(f"[planner] fallback reason={type(exc).__name__}: {exc}")
        print(f"[planner] fallback to deterministic planner: {type(exc).__name__}: {exc}")
        return _deterministic_plan(context, used_fallback=True)
