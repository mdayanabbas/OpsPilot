from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class IncidentExecutionTrace(Base):
    __tablename__ = "incident_execution_traces"

    id = Column(Integer, primary_key=True, index=True)
    incident_id = Column(
        Integer,
        ForeignKey("incidents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    response_plan_id = Column(
        Integer,
        ForeignKey("incident_response_plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tool_name = Column(String(100), nullable=False)
    status = Column(String(50), nullable=False)
    result_summary = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    incident = relationship("Incident", back_populates="execution_traces")
    response_plan = relationship("IncidentResponsePlan", back_populates="execution_traces")
