from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String

from app.database import Base


class ProcessedEmail(Base):
    __tablename__ = "processed_emails"

    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(String(255), nullable=False, unique=True, index=True)
    from_email = Column(String(255), nullable=True)
    subject = Column(String(500), nullable=True)
    workflow_run_id = Column(Integer, nullable=True)
    processed_at = Column(DateTime, nullable=False, default=datetime.utcnow)
