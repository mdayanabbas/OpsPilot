from sqlalchemy import Boolean, Column, Float, ForeignKey, Integer, Text
from sqlalchemy.orm import relationship

from app.database import Base


class EvaluationResult(Base):
    __tablename__ = "evaluation_results"

    id = Column(Integer, primary_key=True, index=True)

    workflow_run_id = Column(Integer, ForeignKey("workflow_runs.id", ondelete="CASCADE"), nullable=False, unique=True)

    quality_score = Column(Float, nullable=True)
    reply_policy_compliance = Column(Float, nullable=True)
    ticket_completeness = Column(Float, nullable=True)
    unsupported_claim_rate = Column(Float, nullable=True)
    tool_recovery_success = Column(Float, nullable=True)

    requires_human_review = Column(Boolean, nullable=False, default=False)
    risks = Column(Text, nullable=True)

    workflow_run = relationship("WorkflowRun", back_populates="evaluation_result")