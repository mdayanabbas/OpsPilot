from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class CriticResult(Base):
    __tablename__ = "critic_results"

    id = Column(Integer, primary_key=True, index=True)
    workflow_run_id = Column(Integer, ForeignKey("workflow_runs.id", ondelete="CASCADE"), nullable=False)

    critic_status = Column(String(50), nullable=False)
    risk_flags = Column(Text, nullable=False)
    quality_notes = Column(Text, nullable=False)
    recommended_action = Column(Text, nullable=False)
    requires_manual_review = Column(Boolean, nullable=False, default=False)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    workflow_run = relationship("WorkflowRun", back_populates="critic_results")
