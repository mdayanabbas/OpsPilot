from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class ApprovalComment(Base):
    __tablename__ = "approval_comments"

    id = Column(Integer, primary_key=True, index=True)
    approval_id = Column(
        Integer,
        ForeignKey("approval_decisions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reviewer = Column(String(150), nullable=False)
    comment = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    approval = relationship("ApprovalDecision", back_populates="comments")
