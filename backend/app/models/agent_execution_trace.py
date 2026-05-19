from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class AgentExecutionTrace(Base):
    __tablename__ = "agent_execution_traces"

    id = Column(Integer, primary_key=True, index=True)
    workflow_run_id = Column(Integer, ForeignKey("workflow_runs.id", ondelete="CASCADE"), nullable=False)
    planner_decision_id = Column(Integer, ForeignKey("planner_decisions.id", ondelete="CASCADE"), nullable=False)

    tool_name = Column(String(100), nullable=False)
    status = Column(String(50), nullable=False)
    result_summary = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    workflow_run = relationship("WorkflowRun", back_populates="agent_execution_traces")
    planner_decision = relationship("PlannerDecision", back_populates="execution_traces")
