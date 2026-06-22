"""Deterministic system regression evaluation for OpsPilot workflows."""

import json
from pathlib import Path

from app.models.benchmark_expectation import BenchmarkExpectation
from app.models.benchmark_result import BenchmarkResult
from app.models.benchmark_run import BenchmarkRun
from app.models.critic_result import CriticResult
from app.models.evaluation import EvaluationResult
from app.models.planner_decision import PlannerDecision
from app.models.ticket import Ticket
from app.schemas.workflow_schema import WorkflowRunCreate


REGRESSION_CASES_FILE = (
    Path(__file__).resolve().parents[3]
    / "benchmarks"
    / "regression_cases"
    / "v1.json"
)
CHECK_FIELDS = {
    "category_match": "ticket.category",
    "planner_match": "planner.plan_type",
    "priority_match": "ticket.priority",
    "approval_match": "ticket.requires_approval",
    "workflow_status_match": "workflow.status",
    "critic_match": "critic.critic_status",
}


def load_regression_cases() -> list[dict]:
    with REGRESSION_CASES_FILE.open("r", encoding="utf-8") as case_file:
        cases = json.load(case_file)
    return cases if isinstance(cases, list) else []


def _latest(db, model, workflow_run_id: int):
    return (
        db.query(model)
        .filter(model.workflow_run_id == workflow_run_id)
        .order_by(model.id.desc())
        .first()
    )


def _sync_expectation(db, benchmark_case: dict) -> BenchmarkExpectation:
    case_id = str(benchmark_case["id"])
    values = benchmark_case["expectation"]
    expectation = (
        db.query(BenchmarkExpectation)
        .filter(BenchmarkExpectation.benchmark_case_id == case_id)
        .first()
    )
    if not expectation:
        expectation = BenchmarkExpectation(benchmark_case_id=case_id)
        db.add(expectation)
    for key, value in values.items():
        setattr(expectation, key, value)
    db.flush()
    return expectation


def evaluate_benchmark_case(db, benchmark_case, workflow_run) -> dict:
    """Compare six persisted workflow outputs without using an LLM."""
    expectation = (
        db.query(BenchmarkExpectation)
        .filter(
            BenchmarkExpectation.benchmark_case_id == str(benchmark_case["id"])
        )
        .first()
    )
    if not expectation:
        expectation = _sync_expectation(db, benchmark_case)

    ticket = _latest(db, Ticket, workflow_run.id)
    planner = _latest(db, PlannerDecision, workflow_run.id)
    critic = _latest(db, CriticResult, workflow_run.id)
    matches = {
        "category_match": bool(ticket) and ticket.category == expectation.expected_category,
        "planner_match": bool(planner) and planner.plan_type == expectation.expected_plan_type,
        "priority_match": bool(ticket) and ticket.priority == expectation.expected_priority,
        "approval_match": bool(ticket) and ticket.requires_approval == expectation.expected_requires_approval,
        "workflow_status_match": workflow_run.status == expectation.expected_workflow_status,
        "critic_match": bool(critic) and critic.critic_status == expectation.expected_critic_status,
    }
    total_score = sum(matches.values()) / 6
    result = BenchmarkResult(
        benchmark_case_id=str(benchmark_case["id"]),
        workflow_run_id=workflow_run.id,
        total_score=round(total_score, 4),
        **matches,
    )
    db.add(result)
    db.flush()
    return {
        "id": result.id,
        "benchmark_case_id": result.benchmark_case_id,
        "workflow_run_id": result.workflow_run_id,
        **matches,
        "total_score": result.total_score,
        "passed": total_score == 1.0,
        "mismatches": [
            field for key, field in CHECK_FIELDS.items() if not matches[key]
        ],
    }


def _failed_result(db, benchmark_case: dict) -> dict:
    matches = {key: False for key in CHECK_FIELDS}
    result = BenchmarkResult(
        benchmark_case_id=str(benchmark_case["id"]),
        workflow_run_id=None,
        total_score=0.0,
        **matches,
    )
    db.add(result)
    db.flush()
    return {
        "id": result.id,
        "benchmark_case_id": result.benchmark_case_id,
        "workflow_run_id": None,
        **matches,
        "total_score": 0.0,
        "passed": False,
        "mismatches": list(CHECK_FIELDS.values()),
    }


def run_benchmark_suite(db, suite_name: str = "regression_v1") -> dict:
    cases = load_regression_cases()
    results = []

    # Lazy import avoids making API routing a dependency during evaluator import.
    from app.api.v1.workflow_routes import _execute_workflow_run_sync

    for benchmark_case in cases:
        _sync_expectation(db, benchmark_case)
        try:
            workflow_run = _execute_workflow_run_sync(
                payload=WorkflowRunCreate(input_text=benchmark_case["input_text"]),
                db=db,
            )
            results.append(
                evaluate_benchmark_case(db, benchmark_case, workflow_run)
            )
        except Exception:
            db.rollback()
            _sync_expectation(db, benchmark_case)
            results.append(_failed_result(db, benchmark_case))
        db.commit()

    cases_run = len(results)
    average = lambda key: (
        sum(float(result[key]) for result in results) / cases_run
        if cases_run
        else 0.0
    )
    avg_score = average("total_score")
    planner_accuracy = average("planner_match")
    category_accuracy = average("category_match")
    priority_accuracy = average("priority_match")
    critic_accuracy = average("critic_match")
    passed_cases = sum(result["passed"] for result in results)

    benchmark_run = BenchmarkRun(
        suite_name=suite_name,
        cases_run=cases_run,
        avg_score=round(avg_score, 4),
        planner_accuracy=round(planner_accuracy, 4),
        category_accuracy=round(category_accuracy, 4),
        priority_accuracy=round(priority_accuracy, 4),
        critic_accuracy=round(critic_accuracy, 4),
        total_cases=cases_run,
        passed_cases=passed_cases,
        failed_cases=cases_run - passed_cases,
        pass_rate=round(passed_cases / cases_run, 4) if cases_run else 0.0,
        average_quality_score=round(avg_score, 4),
    )
    db.add(benchmark_run)
    db.commit()
    db.refresh(benchmark_run)

    return {
        "id": benchmark_run.id,
        "suite_name": suite_name,
        "cases_run": cases_run,
        "avg_score": benchmark_run.avg_score,
        "planner_accuracy": benchmark_run.planner_accuracy,
        "category_accuracy": benchmark_run.category_accuracy,
        "priority_accuracy": benchmark_run.priority_accuracy,
        "critic_accuracy": benchmark_run.critic_accuracy,
        "results": results,
        "created_at": benchmark_run.created_at,
    }


def benchmark_result_payload(result: BenchmarkResult) -> dict:
    matches = {key: bool(getattr(result, key)) for key in CHECK_FIELDS}
    return {
        "id": result.id,
        "benchmark_case_id": result.benchmark_case_id,
        "workflow_run_id": result.workflow_run_id,
        **matches,
        "total_score": result.total_score,
        "passed": result.total_score == 1.0,
        "mismatches": [
            field for key, field in CHECK_FIELDS.items() if not matches[key]
        ],
        "created_at": result.created_at,
    }
