from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.benchmark_run import BenchmarkRun


class BenchmarkCaseResult(Base):
    __tablename__ = "benchmark_case_results"

    id = Column(Integer, primary_key=True, index=True)
    benchmark_run_id = Column(Integer, ForeignKey("benchmark_runs.id", ondelete="CASCADE"), nullable=False)
    case_id = Column(String(100), nullable=False)
    passed = Column(Boolean, nullable=False, default=False)
    failures = Column(Text, nullable=True)
    workflow_run_id = Column(Integer, ForeignKey("workflow_runs.id", ondelete="SET NULL"), nullable=True)

    benchmark_run = relationship("BenchmarkRun", back_populates="case_results")
