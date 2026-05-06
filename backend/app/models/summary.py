from sqlalchemy import Column, ForeignKey, Integer, Text
from sqlalchemy.orm import relationship

from app.database import Base


class FounderSummary(Base):
    __tablename__ = "founder_summaries"

    id = Column(Integer, primary_key=True, index=True)

    workflow_run_id = Column(Integer, ForeignKey("workflow_runs.id", ondelete="CASCADE"), nullable=False, unique=True)

    summary = Column(Text, nullable=False)
    risks = Column(Text, nullable=True)
    recommended_actions = Column(Text, nullable=True)

    workflow_run = relationship("WorkflowRun", back_populates="founder_summary")