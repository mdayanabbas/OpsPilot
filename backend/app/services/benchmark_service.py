import json
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.api.v1.workflow_routes import create_workflow_run
from app.models.evaluation import EvaluationResult
from app.models.reply import CustomerReply
from app.models.ticket import Ticket
from app.schemas.workflow_schema import WorkflowRunCreate


BENCHMARK_CASES_DIR = Path(__file__).resolve().parents[3] / "benchmarks" / "cases"


def load_benchmark_cases() -> list[dict[str, Any]]:
    cases = []

    for case_path in sorted(BENCHMARK_CASES_DIR.glob("*.json")):
        with case_path.open("r", encoding="utf-8") as case_file:
            cases.append(json.load(case_file))

    return cases


def _check_expected_outputs(
    expected: dict[str, Any],
    tickets: list[Ticket],
    replies: list[CustomerReply],
    evaluation: EvaluationResult | None,
) -> list[str]:
    failures = []

    should_create_ticket = expected.get("should_create_ticket")
    if should_create_ticket is not None and bool(tickets) != should_create_ticket:
        failures.append(
            f"Expected should_create_ticket={should_create_ticket}, got {bool(tickets)}."
        )

    should_create_reply = expected.get("should_create_reply")
    if should_create_reply is not None and bool(replies) != should_create_reply:
        failures.append(
            f"Expected should_create_reply={should_create_reply}, got {bool(replies)}."
        )

    should_require_human_review = expected.get("should_require_human_review")
    if should_require_human_review is not None and evaluation is not None:
        if evaluation.requires_human_review != should_require_human_review:
            failures.append(
                "Expected should_require_human_review="
                f"{should_require_human_review}, got {evaluation.requires_human_review}."
            )

    expected_min_quality_score = expected.get("expected_min_quality_score")
    if expected_min_quality_score is not None and evaluation is not None:
        quality_score = evaluation.quality_score or 0.0
        if quality_score < expected_min_quality_score:
            failures.append(
                f"Expected quality_score >= {expected_min_quality_score}, got {quality_score}."
            )

    expected_issue_category = expected.get("expected_issue_category")
    if expected_issue_category is not None and tickets:
        actual_category = tickets[0].category
        if actual_category != expected_issue_category:
            failures.append(
                f"Expected first ticket category {expected_issue_category}, got {actual_category}."
            )

    return failures


def run_benchmarks(db: Session) -> dict:
    cases = load_benchmark_cases()
    results = []
    quality_scores = []

    for benchmark_case in cases:
        failures = []
        workflow_run_id = None

        try:
            payload = WorkflowRunCreate(input_text=benchmark_case["input_text"])
            workflow_run = create_workflow_run(payload=payload, db=db)
            workflow_run_id = workflow_run.id

            tickets = (
                db.query(Ticket)
                .filter(Ticket.workflow_run_id == workflow_run_id)
                .all()
            )
            replies = (
                db.query(CustomerReply)
                .filter(CustomerReply.workflow_run_id == workflow_run_id)
                .all()
            )
            evaluation = (
                db.query(EvaluationResult)
                .filter(EvaluationResult.workflow_run_id == workflow_run_id)
                .first()
            )

            failures.extend(
                _check_expected_outputs(
                    expected=benchmark_case.get("expected", {}),
                    tickets=tickets,
                    replies=replies,
                    evaluation=evaluation,
                )
            )

            if evaluation and evaluation.quality_score is not None:
                quality_scores.append(evaluation.quality_score)

        except Exception as exc:
            failures.append(f"Benchmark execution failed: {type(exc).__name__}: {exc}")

        results.append(
            {
                "case_id": benchmark_case.get("id"),
                "passed": not failures,
                "failures": failures,
                "workflow_run_id": workflow_run_id,
            }
        )

    total_cases = len(results)
    passed_cases = sum(1 for result in results if result["passed"])
    failed_cases = total_cases - passed_cases
    pass_rate = passed_cases / total_cases if total_cases else 0.0
    average_quality_score = (
        sum(quality_scores) / len(quality_scores)
        if quality_scores
        else 0.0
    )

    return {
        "total_cases": total_cases,
        "passed_cases": passed_cases,
        "failed_cases": failed_cases,
        "pass_rate": round(pass_rate, 2),
        "average_quality_score": round(average_quality_score, 2),
        "results": results,
    }
