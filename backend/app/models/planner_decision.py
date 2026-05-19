from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class PlannerDecision(Base):
    __tablename__ = "planner_decisions"

    id = Column(Integer, primary_key=True, index=True)
    workflow_run_id = Column(Integer, ForeignKey("workflow_runs.id", ondelete="CASCADE"), nullable=False)

    plan_type = Column(String(50), nullable=False)
    next_tools = Column(Text, nullable=False)
    requires_human_approval = Column(Boolean, nullable=False, default=False)
    reasoning_summary = Column(Text, nullable=False)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    workflow_run = relationship("WorkflowRun", back_populates="planner_decisions")
    execution_traces = relationship("AgentExecutionTrace", back_populates="planner_decision", cascade="all, delete-orphan")
