"""Read-only executive aggregation across OpsPilot operational records."""

from __future__ import annotations

import json
from datetime import datetime, time

from sqlalchemy import func

from app.models.approval import ApprovalDecision
from app.models.benchmark_run import BenchmarkRun
from app.models.critic_result import CriticResult
from app.models.incident import Incident
from app.models.reply import CustomerReply
from app.models.ticket import Ticket
from app.models.tool_call import ToolCall
from app.models.workflow import WorkflowRun


FINAL_APPROVAL_STATES = {"approved", "rejected"}


def _rate(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 4) if denominator else 0.0


def _benchmark_score(run: BenchmarkRun | None) -> float | None:
    if not run:
        return None
    return round(run.avg_score if run.cases_run else run.pass_rate, 4)


def _incident_risk_text(incident: Incident) -> list[str]:
    if not incident.operational_risks:
        return []
    try:
        parsed = json.loads(incident.operational_risks)
    except (TypeError, json.JSONDecodeError):
        return []
    return [value.strip() for value in parsed if isinstance(value, str) and value.strip()]


def _top_risks(
    incidents: list[Incident],
    pending_approvals: int,
    fallback_rate: float,
    critic_warning_rate: float,
    needs_clarification: int,
) -> list[str]:
    risks: list[str] = []
    critical_count = sum(incident.severity == "critical" for incident in incidents)
    high_count = sum(incident.severity == "high" for incident in incidents)
    if critical_count:
        risks.append(f"{critical_count} critical incident(s) require immediate attention.")
    elif high_count:
        risks.append(f"{high_count} high-severity incident(s) remain open.")

    for incident in incidents:
        for risk in _incident_risk_text(incident):
            if risk not in risks:
                risks.append(risk)
            if len(risks) >= 2:
                break
        if len(risks) >= 2:
            break

    if pending_approvals:
        risks.append(f"{pending_approvals} customer-facing item(s) are awaiting approval.")
    if fallback_rate >= 0.1:
        risks.append(f"Fallback usage is elevated at {round(fallback_rate * 100)}%.")
    if critic_warning_rate >= 0.25:
        risks.append(f"Critic warnings affect {round(critic_warning_rate * 100)}% of reviewed workflows.")
    if needs_clarification:
        risks.append(f"{needs_clarification} workflow(s) are blocked on clarification.")

    return risks[:5] or ["No material operational risks detected."]


def _recent_activity(
    workflows: list[WorkflowRun],
    incidents: list[Incident],
    approvals: list[ApprovalDecision],
    benchmark: BenchmarkRun | None,
) -> list[dict]:
    activity: list[dict] = []
    for workflow in workflows:
        activity.append(
            {
                "type": "workflow",
                "title": f"Workflow #{workflow.id} {workflow.status.replace('_', ' ')}",
                "description": workflow.input_text[:180],
                "created_at": workflow.created_at,
            }
        )
    for incident in incidents:
        activity.append(
            {
                "type": "incident",
                "title": incident.title,
                "description": (
                    f"{incident.severity.title()} {incident.category} incident affecting "
                    f"{incident.workflow_count} workflow(s)."
                ),
                "created_at": incident.last_detected_at,
            }
        )
    for approval in approvals:
        activity.append(
            {
                "type": "approval",
                "title": f"{approval.item_type.replace('_', ' ').title()} {approval.decision}",
                "description": (
                    f"Workflow #{approval.workflow_run_id} · item #{approval.item_id}"
                ),
                "created_at": approval.created_at,
            }
        )
    if benchmark:
        score = _benchmark_score(benchmark)
        activity.append(
            {
                "type": "benchmark",
                "title": f"Benchmark run #{benchmark.id} completed",
                "description": (
                    f"{benchmark.suite_name} scored "
                    f"{round((score or 0) * 100, 1)}% across "
                    f"{benchmark.cases_run or benchmark.total_cases} case(s)."
                ),
                "created_at": benchmark.created_at,
            }
        )
    activity.sort(key=lambda item: item["created_at"], reverse=True)
    return activity[:12]


def get_executive_summary(db) -> dict:
    today_start = datetime.combine(datetime.utcnow().date(), time.min)
    total_workflows = db.query(WorkflowRun).count()
    workflows_today = (
        db.query(WorkflowRun).filter(WorkflowRun.created_at >= today_start).count()
    )
    completed_workflows = (
        db.query(WorkflowRun).filter(WorkflowRun.status == "completed").count()
    )
    needs_clarification = (
        db.query(WorkflowRun)
        .filter(WorkflowRun.status == "needs_clarification")
        .count()
    )
    review_workflows = (
        db.query(func.count(func.distinct(CriticResult.workflow_run_id)))
        .join(WorkflowRun, WorkflowRun.id == CriticResult.workflow_run_id)
        .filter(
            WorkflowRun.status == "completed",
            CriticResult.requires_manual_review.is_(True),
        )
        .scalar()
        or 0
    )
    human_review_rate = _rate(review_workflows, completed_workflows)
    automation_rate = round(max(0.0, 1.0 - human_review_rate), 4)

    open_incident_rows = (
        db.query(Incident)
        .filter(Incident.status == "active")
        .order_by(Incident.last_detected_at.desc())
        .all()
    )
    critical_incidents = sum(row.severity == "critical" for row in open_incident_rows)
    high_incidents = sum(row.severity == "high" for row in open_incident_rows)
    top_category_row = (
        db.query(Incident.category, func.count(Incident.id).label("incident_count"))
        .filter(Incident.status == "active")
        .group_by(Incident.category)
        .order_by(func.count(Incident.id).desc(), Incident.category.asc())
        .first()
    )

    pending_approvals = (
        db.query(Ticket)
        .filter(
            Ticket.requires_approval.is_(True),
            Ticket.status.notin_(FINAL_APPROVAL_STATES),
        )
        .count()
        + db.query(CustomerReply)
        .filter(
            CustomerReply.requires_approval.is_(True),
            CustomerReply.status.notin_(FINAL_APPROVAL_STATES),
        )
        .count()
    )
    approved_today = (
        db.query(ApprovalDecision)
        .filter(
            ApprovalDecision.decision == "approved",
            ApprovalDecision.created_at >= today_start,
        )
        .count()
    )
    rejected_today = (
        db.query(ApprovalDecision)
        .filter(
            ApprovalDecision.decision == "rejected",
            ApprovalDecision.created_at >= today_start,
        )
        .count()
    )

    benchmark_runs = (
        db.query(BenchmarkRun)
        .order_by(BenchmarkRun.created_at.desc(), BenchmarkRun.id.desc())
        .limit(2)
        .all()
    )
    latest_benchmark = benchmark_runs[0] if benchmark_runs else None
    previous_benchmark = benchmark_runs[1] if len(benchmark_runs) > 1 else None
    latest_benchmark_score = _benchmark_score(latest_benchmark)
    previous_benchmark_score = _benchmark_score(previous_benchmark)
    benchmark_trend = (
        round(latest_benchmark_score - previous_benchmark_score, 4)
        if latest_benchmark_score is not None and previous_benchmark_score is not None
        else None
    )

    total_tool_calls = db.query(ToolCall).count()
    fallback_count = (
        db.query(ToolCall).filter(ToolCall.fallback_used.is_(True)).count()
    )
    fallback_rate = _rate(fallback_count, total_tool_calls)
    critic_count = db.query(CriticResult).count()
    critic_warning_count = (
        db.query(CriticResult)
        .filter(CriticResult.critic_status.in_(("warning", "blocked")))
        .count()
    )
    critic_warning_rate = _rate(critic_warning_count, critic_count)

    latest_workflows = (
        db.query(WorkflowRun).order_by(WorkflowRun.created_at.desc()).limit(5).all()
    )
    latest_incidents = open_incident_rows[:3]
    latest_approvals = (
        db.query(ApprovalDecision)
        .filter(ApprovalDecision.decision.in_(FINAL_APPROVAL_STATES))
        .order_by(ApprovalDecision.created_at.desc())
        .limit(3)
        .all()
    )

    return {
        "workflows_today": workflows_today,
        "total_workflows": total_workflows,
        "completed_workflows": completed_workflows,
        "needs_clarification": needs_clarification,
        "automation_rate": automation_rate,
        "human_review_rate": human_review_rate,
        "open_incidents": len(open_incident_rows),
        "critical_incidents": critical_incidents,
        "high_incidents": high_incidents,
        "top_incident_category": top_category_row[0] if top_category_row else None,
        "pending_approvals": pending_approvals,
        "approved_today": approved_today,
        "rejected_today": rejected_today,
        "latest_benchmark_score": latest_benchmark_score,
        "benchmark_trend": benchmark_trend,
        "fallback_rate": fallback_rate,
        "critic_warning_rate": critic_warning_rate,
        "top_risks": _top_risks(
            open_incident_rows,
            pending_approvals,
            fallback_rate,
            critic_warning_rate,
            needs_clarification,
        ),
        "recent_activity": _recent_activity(
            latest_workflows,
            latest_incidents,
            latest_approvals,
            latest_benchmark,
        ),
    }
