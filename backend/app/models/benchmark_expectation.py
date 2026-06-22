from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String

from app.database import Base


class BenchmarkExpectation(Base):
    __tablename__ = "benchmark_expectations"

    id = Column(Integer, primary_key=True, index=True)
    benchmark_case_id = Column(String(150), nullable=False, unique=True, index=True)
    expected_category = Column(String(100), nullable=False)
    expected_plan_type = Column(String(100), nullable=False)
    expected_priority = Column(String(50), nullable=False)
    expected_requires_approval = Column(Boolean, nullable=False)
    expected_workflow_status = Column(String(50), nullable=False)
    expected_critic_status = Column(String(50), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
