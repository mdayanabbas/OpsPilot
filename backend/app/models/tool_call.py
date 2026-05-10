from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class ToolCall(Base):
    __tablename__ = "tool_calls"

    id = Column(Integer, primary_key=True, index=True)

    workflow_run_id = Column(Integer, ForeignKey("workflow_runs.id", ondelete="CASCADE"), nullable=False)

    step_name = Column(String(100), nullable=False)
    tool_name = Column(String(100), nullable=False)
    provider = Column(String(50), nullable=False, default="gemini")

    status = Column(String(50), nullable=False, default="pending")
    attempt = Column(Integer, nullable=False, default=1)

    latency_ms = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    fallback_used = Column(Boolean, nullable=False, default=False)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    workflow_run = relationship("WorkflowRun", back_populates="tool_calls")
