from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text

from app.database import Base


class Incident(Base):
    __tablename__ = "incidents"

    id = Column(Integer, primary_key=True, index=True)
    category = Column(String(100), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    severity = Column(String(50), nullable=False)
    workflow_count = Column(Integer, nullable=False, default=0)
    root_cause_summary = Column(Text, nullable=True)
    operational_risks = Column(Text, nullable=True)
    recommended_actions = Column(Text, nullable=True)
    first_detected_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_detected_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    status = Column(String(50), nullable=False, default="active")
