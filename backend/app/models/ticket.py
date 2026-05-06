from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, index=True)

    workflow_run_id = Column(Integer, ForeignKey("workflow_runs.id", ondelete="CASCADE"), nullable=False)

    title = Column(String(255), nullable=False)
    priority = Column(String(50), nullable=False, default="medium")
    team = Column(String(100), nullable=True)
    category = Column(String(100), nullable=True)

    description = Column(Text, nullable=False)
    acceptance_criteria = Column(Text, nullable=True)
    source_evidence = Column(Text, nullable=True)

    requires_approval = Column(Boolean, nullable=False, default=True)
    status = Column(String(50), nullable=False, default="draft")

    workflow_run = relationship("WorkflowRun", back_populates="tickets")