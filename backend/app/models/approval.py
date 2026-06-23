from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class ApprovalDecision(Base):
    __tablename__ = "approval_decisions"

    id = Column(Integer, primary_key=True, index=True)

    workflow_run_id = Column(Integer, ForeignKey("workflow_runs.id", ondelete="CASCADE"), nullable=False)

    item_type = Column(String(50), nullable=False)
    item_id = Column(Integer, nullable=False)

    decision = Column(String(50), nullable=False, default="pending")
    reviewer_note = Column(Text, nullable=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    workflow_run = relationship("WorkflowRun", back_populates="approval_decisions")
    comments = relationship(
        "ApprovalComment",
        back_populates="approval",
        cascade="all, delete-orphan",
        order_by="ApprovalComment.created_at",
    )
