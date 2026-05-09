from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.benchmark_service import load_benchmark_cases, run_benchmarks

router = APIRouter()


@router.get("/")
def list_benchmarks():
    return {"message": "Benchmarks module coming soon"}


@router.get("/cases")
def list_benchmark_cases():
    return load_benchmark_cases()


@router.post("/run")
def run_benchmark_suite(db: Session = Depends(get_db)):
    return run_benchmarks(db)
