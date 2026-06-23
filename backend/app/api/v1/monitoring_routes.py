from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.evaluation import EvaluationResult
from app.models.tool_call import ToolCall
from app.models.workflow import WorkflowRun
from app.services.executive_summary_service import get_executive_summary

router = APIRouter()


@router.get("/executive-summary")
def executive_summary(db: Session = Depends(get_db)):
    return get_executive_summary(db)


def _safe_provider(tool_call: ToolCall) -> str:
    provider = getattr(tool_call, "provider", None)
    if provider:
        return provider

    tool_name = (tool_call.tool_name or "").lower()
    if "local" in tool_name or "lm_studio" in tool_name or "lm-studio" in tool_name:
        return "local"
    if "fallback" in tool_name or tool_call.fallback_used:
        return "fallback"
    if "gemini" in tool_name:
        return "gemini"
    return "unknown"


def _avg(values: list[float | None]) -> float:
    numeric_values = [value for value in values if value is not None]
    if not numeric_values:
        return 0.0
    return round(sum(numeric_values) / len(numeric_values), 2)


@router.get("/summary")
def get_monitoring_summary(db: Session = Depends(get_db)):
    total_workflows = db.query(WorkflowRun).count()
    completed_workflows = db.query(WorkflowRun).filter(WorkflowRun.status == "completed").count()
    failed_workflows = db.query(WorkflowRun).filter(WorkflowRun.status == "failed").count()
    needs_clarification_workflows = (
        db.query(WorkflowRun)
        .filter(WorkflowRun.status == "needs_clarification")
        .count()
    )

    total_tool_calls = db.query(ToolCall).count()
    successful_tool_calls = db.query(ToolCall).filter(ToolCall.status == "success").count()
    failed_tool_calls = db.query(ToolCall).filter(ToolCall.status == "failed").count()
    fallback_count = db.query(ToolCall).filter(ToolCall.fallback_used.is_(True)).count()
    fallback_rate = round(fallback_count / total_tool_calls, 2) if total_tool_calls else 0.0

    evaluation_rows = db.query(EvaluationResult).all()
    average_quality_score = _avg([evaluation.quality_score for evaluation in evaluation_rows])
    average_tool_recovery_success = _avg(
        [evaluation.tool_recovery_success for evaluation in evaluation_rows]
    )

    provider_breakdown: dict[str, int] = {}
    for tool_call in db.query(ToolCall).all():
        provider = _safe_provider(tool_call)
        provider_breakdown[provider] = provider_breakdown.get(provider, 0) + 1

    latest_failed_tool_calls = (
        db.query(ToolCall)
        .filter(ToolCall.status == "failed")
        .order_by(ToolCall.created_at.desc())
        .limit(5)
        .all()
    )

    return {
        "total_workflows": total_workflows,
        "completed_workflows": completed_workflows,
        "failed_workflows": failed_workflows,
        "needs_clarification_workflows": needs_clarification_workflows,
        "total_tool_calls": total_tool_calls,
        "successful_tool_calls": successful_tool_calls,
        "failed_tool_calls": failed_tool_calls,
        "fallback_count": fallback_count,
        "fallback_rate": fallback_rate,
        "average_quality_score": average_quality_score,
        "average_tool_recovery_success": average_tool_recovery_success,
        "provider_breakdown": provider_breakdown,
        "latest_failed_tool_calls": [
            {
                "workflow_run_id": tool_call.workflow_run_id,
                "step_name": tool_call.step_name,
                "tool_name": tool_call.tool_name,
                "provider": _safe_provider(tool_call),
                "error_message": tool_call.error_message,
                "created_at": tool_call.created_at,
            }
            for tool_call in latest_failed_tool_calls
        ],
    }
