from datetime import datetime
from sqlalchemy import Column, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class WorkflowRun(Base):
    __tablename__ = "workflow_runs"

    id = Column(Integer, primary_key=True, index=True)

    input_text = Column(Text, nullable=False)
    status = Column(String(50), nullable=False, default="pending")
    workflow_type = Column(String(100), nullable=False, default="customer_feedback_triage")
    confidence = Column(Float, nullable=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    agent_steps = relationship("AgentStep", back_populates="workflow_run", cascade="all, delete-orphan")
    tool_calls = relationship("ToolCall", back_populates="workflow_run", cascade="all, delete-orphan")
    tickets = relationship("Ticket", back_populates="workflow_run", cascade="all, delete-orphan")
    customer_replies = relationship("CustomerReply", back_populates="workflow_run", cascade="all, delete-orphan")
    founder_summary = relationship("FounderSummary", back_populates="workflow_run", uselist=False, cascade="all, delete-orphan")
    evaluation_result = relationship("EvaluationResult", back_populates="workflow_run", uselist=False, cascade="all, delete-orphan")
    approval_decisions = relationship("ApprovalDecision", back_populates="workflow_run", cascade="all, delete-orphan")
    memory_items = relationship("MemoryItem", back_populates="workflow_run", cascade="all, delete-orphan")
    critic_results = relationship("CriticResult", back_populates="workflow_run", cascade="all, delete-orphan")
    planner_decisions = relationship("PlannerDecision", back_populates="workflow_run", cascade="all, delete-orphan")
