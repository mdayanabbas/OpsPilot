from datetime import datetime
from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class AgentStep(Base):
    __tablename__ = "agent_steps"

    id = Column(Integer, primary_key=True, index=True)

    workflow_run_id = Column(Integer, ForeignKey("workflow_runs.id", ondelete="CASCADE"), nullable=False)

    step_name = Column(String(100), nullable=False)
    status = Column(String(50), nullable=False, default="pending")

    input_summary = Column(Text, nullable=True)
    output_summary = Column(Text, nullable=True)

    confidence = Column(Float, nullable=True)
    latency_ms = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    workflow_run = relationship("WorkflowRun", back_populates="agent_steps")