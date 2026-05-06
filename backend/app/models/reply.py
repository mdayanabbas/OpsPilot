from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class CustomerReply(Base):
    __tablename__ = "customer_replies"

    id = Column(Integer, primary_key=True, index=True)

    workflow_run_id = Column(Integer, ForeignKey("workflow_runs.id", ondelete="CASCADE"), nullable=False)

    customer = Column(String(255), nullable=True)
    issue = Column(Text, nullable=False)

    draft_reply = Column(Text, nullable=True)

    risk_level = Column(String(50), nullable=False, default="low")
    risk_reason = Column(Text, nullable=True)

    requires_approval = Column(Boolean, nullable=False, default=True)
    status = Column(String(50), nullable=False, default="draft")

    workflow_run = relationship("WorkflowRun", back_populates="customer_replies")