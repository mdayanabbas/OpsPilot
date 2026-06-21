"""Observational workflow replay and persisted-output comparison."""

from app.models.critic_result import CriticResult
from app.models.evaluation import EvaluationResult
from app.models.planner_decision import PlannerDecision
from app.models.reply import CustomerReply
from app.models.ticket import Ticket
from app.models.tool_call import ToolCall
from app.models.workflow import WorkflowRun
from app.models.workflow_replay import WorkflowReplay


def _latest(db, model, workflow_run_id: int):
    return (
        db.query(model)
        .filter(model.workflow_run_id == workflow_run_id)
        .order_by(model.id.desc())
        .first()
    )


def _snapshot(db, workflow_run_id: int) -> dict:
    workflow = db.query(WorkflowRun).filter(WorkflowRun.id == workflow_run_id).first()
    if not workflow:
        raise ValueError(f"Workflow run {workflow_run_id} was not found.")

    ticket = _latest(db, Ticket, workflow_run_id)
    reply = _latest(db, CustomerReply, workflow_run_id)
    evaluation = _latest(db, EvaluationResult, workflow_run_id)
    critic = _latest(db, CriticResult, workflow_run_id)
    planner = _latest(db, PlannerDecision, workflow_run_id)
    return {
        "workflow.status": workflow.status,
        "workflow.workflow_type": workflow.workflow_type,
        "workflow.confidence": workflow.confidence,
        "ticket.category": ticket.category if ticket else None,
        "ticket.priority": ticket.priority if ticket else None,
        "ticket.title": ticket.title if ticket else None,
        "ticket.requires_approval": ticket.requires_approval if ticket else None,
        "reply.risk_level": reply.risk_level if reply else None,
        "evaluation.quality_score": evaluation.quality_score if evaluation else None,
        "critic.critic_status": critic.critic_status if critic else None,
        "planner.plan_type": planner.plan_type if planner else None,
    }


def compare_workflow_runs(
    db,
    source_workflow_run_id: int,
    replay_workflow_run_id: int,
) -> dict:
    before = _snapshot(db, source_workflow_run_id)
    after = _snapshot(db, replay_workflow_run_id)
    changes = [
        {"field": field, "before": before[field], "after": after[field]}
        for field in before
        if before[field] != after[field]
    ]
    summary = (
        f"{len(changes)} compared field(s) changed: "
        + ", ".join(change["field"] for change in changes)
        if changes
        else "No compared workflow fields changed."
    )
    return {
        "source_workflow_run_id": source_workflow_run_id,
        "replay_workflow_run_id": replay_workflow_run_id,
        "changed": bool(changes),
        "changes": changes,
        "summary": summary,
    }


def replay_workflow_run(db, source_workflow_run_id: int) -> dict:
    source = (
        db.query(WorkflowRun)
        .filter(WorkflowRun.id == source_workflow_run_id)
        .first()
    )
    if not source:
        raise ValueError(f"Workflow run {source_workflow_run_id} was not found.")

    replay_run = WorkflowRun(
        input_text=source.input_text,
        status="running",
        workflow_type="customer_feedback_triage",
        confidence=None,
    )
    db.add(replay_run)
    db.flush()

    replay = WorkflowReplay(
        source_workflow_run_id=source.id,
        replay_workflow_run_id=replay_run.id,
        status="running",
    )
    db.add(replay)
    db.commit()
    db.refresh(replay_run)
    db.refresh(replay)

    try:
        # Lazy imports keep the existing route module as the single workflow runner in v1.
        from app.api.v1.workflow_routes import _execute_workflow_run_sync
        from app.schemas.workflow_schema import WorkflowRunCreate

        _execute_workflow_run_sync(
            payload=WorkflowRunCreate(input_text=source.input_text),
            db=db,
            workflow_run_id=replay_run.id,
        )
        diff = compare_workflow_runs(db, source.id, replay_run.id)
        replay.status = "completed"
        replay.diff_summary = diff["summary"]
        db.add(
            ToolCall(
                workflow_run_id=replay_run.id,
                step_name="workflow_replay",
                tool_name="workflow_replay_service",
                provider="deterministic",
                status="success",
                attempt=1,
                fallback_used=False,
                error_message=None,
            )
        )
        db.commit()
    except Exception as exc:
        replay.status = "failed"
        replay.diff_summary = f"Replay failed: {exc}"
        db.add(
            ToolCall(
                workflow_run_id=replay_run.id,
                step_name="workflow_replay",
                tool_name="workflow_replay_service",
                provider="deterministic",
                status="failed",
                attempt=1,
                fallback_used=False,
                error_message=str(exc),
            )
        )
        db.commit()
        raise

    return {
        "replay_id": replay.id,
        **diff,
        "diff_summary": replay.diff_summary,
        "status": replay.status,
        "created_at": replay.created_at,
    }
