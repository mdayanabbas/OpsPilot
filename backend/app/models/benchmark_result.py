from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String

from app.database import Base


class BenchmarkResult(Base):
    __tablename__ = "benchmark_results"

    id = Column(Integer, primary_key=True, index=True)
    benchmark_case_id = Column(String(150), nullable=False, index=True)
    workflow_run_id = Column(
        Integer,
        ForeignKey("workflow_runs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    category_match = Column(Boolean, nullable=False, default=False)
    planner_match = Column(Boolean, nullable=False, default=False)
    priority_match = Column(Boolean, nullable=False, default=False)
    approval_match = Column(Boolean, nullable=False, default=False)
    workflow_status_match = Column(Boolean, nullable=False, default=False)
    critic_match = Column(Boolean, nullable=False, default=False)
    total_score = Column(Float, nullable=False, default=0.0)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
