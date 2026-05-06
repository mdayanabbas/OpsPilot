from pydantic import BaseModel
from typing import Optional


class CustomerReplyResponse(BaseModel):
    id: int
    workflow_run_id: int
    customer: Optional[str]
    issue: str
    draft_reply: Optional[str]
    risk_level: str
    risk_reason: Optional[str]
    requires_approval: bool
    status: str

    class Config:
        from_attributes = True