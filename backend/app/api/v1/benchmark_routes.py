from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.demo_guard import require_demo_api_key
from app.models.benchmark import BenchmarkRun
from app.models.benchmark_result import BenchmarkResult
from app.schemas.benchmark_schema import BenchmarkRunHistoryResponse
from app.services.benchmark_service import load_benchmark_cases, run_benchmarks
from app.services.benchmark_evaluator import (
    benchmark_result_payload,
    load_regression_cases,
    run_benchmark_suite as run_regression_suite,
)

router = APIRouter()


@router.get("/")
def list_benchmarks():
    return {"message": "Benchmarks module coming soon"}


@router.get("/cases")
def list_benchmark_cases():
    return load_benchmark_cases()


@router.get("/regression-cases")
def list_regression_cases():
    return load_regression_cases()


@router.post("/run", dependencies=[Depends(require_demo_api_key)])
def run_benchmark_suite(db: Session = Depends(get_db)):
    return run_benchmarks(db)


@router.get("/history", response_model=list[BenchmarkRunHistoryResponse])
def list_benchmark_history(db: Session = Depends(get_db)):
    return (
        db.query(BenchmarkRun)
        .order_by(BenchmarkRun.created_at.desc())
        .all()
    )


@router.post("/run-regression", dependencies=[Depends(require_demo_api_key)])
def run_benchmark_regression(db: Session = Depends(get_db)):
    return run_regression_suite(db)


@router.get("/regression-history")
def list_regression_history(db: Session = Depends(get_db)):
    runs = (
        db.query(BenchmarkRun)
        .filter(BenchmarkRun.suite_name == "regression_v1")
        .order_by(BenchmarkRun.created_at.desc(), BenchmarkRun.id.desc())
        .all()
    )
    return [
        {
            "id": run.id,
            "suite_name": run.suite_name,
            "cases_run": run.cases_run,
            "avg_score": run.avg_score,
            "planner_accuracy": run.planner_accuracy,
            "category_accuracy": run.category_accuracy,
            "priority_accuracy": run.priority_accuracy,
            "critic_accuracy": run.critic_accuracy,
            "created_at": run.created_at,
        }
        for run in runs
    ]


@router.get("/results")
def list_regression_results(db: Session = Depends(get_db)):
    results = (
        db.query(BenchmarkResult)
        .order_by(BenchmarkResult.created_at.desc(), BenchmarkResult.id.desc())
        .all()
    )
    return [benchmark_result_payload(result) for result in results]
