from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String
from sqlalchemy.orm import relationship

from app.database import Base


class BenchmarkRun(Base):
    __tablename__ = "benchmark_runs"

    id = Column(Integer, primary_key=True, index=True)

    # Legacy benchmark fields retained for API compatibility.
    total_cases = Column(Integer, nullable=False, default=0)
    passed_cases = Column(Integer, nullable=False, default=0)
    failed_cases = Column(Integer, nullable=False, default=0)
    pass_rate = Column(Float, nullable=False, default=0.0)
    average_quality_score = Column(Float, nullable=False, default=0.0)

    # Regression engine v1 fields.
    suite_name = Column(String(150), nullable=False, default="legacy")
    cases_run = Column(Integer, nullable=False, default=0)
    avg_score = Column(Float, nullable=False, default=0.0)
    planner_accuracy = Column(Float, nullable=False, default=0.0)
    category_accuracy = Column(Float, nullable=False, default=0.0)
    priority_accuracy = Column(Float, nullable=False, default=0.0)
    critic_accuracy = Column(Float, nullable=False, default=0.0)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    case_results = relationship(
        "BenchmarkCaseResult",
        back_populates="benchmark_run",
        cascade="all, delete-orphan",
    )
