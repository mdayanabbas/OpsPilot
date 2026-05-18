from datetime import datetime

from pydantic import BaseModel


class CriticResultResponse(BaseModel):
    id: int
    workflow_run_id: int
    critic_status: str
    risk_flags: list[str]
    quality_notes: list[str]
    recommended_action: str
    requires_manual_review: bool
    created_at: datetime
