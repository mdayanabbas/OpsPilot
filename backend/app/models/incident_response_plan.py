from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class IncidentResponsePlan(Base):
    __tablename__ = "incident_response_plans"

    id = Column(Integer, primary_key=True, index=True)
    incident_id = Column(
        Integer,
        ForeignKey("incidents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    plan_type = Column(String(100), nullable=False)
    next_tools = Column(Text, nullable=False)
    reasoning = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    incident = relationship("Incident", back_populates="response_plans")
