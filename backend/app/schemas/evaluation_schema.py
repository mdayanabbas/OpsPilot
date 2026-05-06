from pydantic import BaseModel
from typing import Optional


class EvaluationResultResponse(BaseModel):
    id: int
    workflow_run_id: int
    quality_score: Optional[float]
    reply_policy_compliance: Optional[float]
    ticket_completeness: Optional[float]
    unsupported_claim_rate: Optional[float]
    tool_recovery_success: Optional[float]
    requires_human_review: bool
    risks: Optional[str]

    class Config:
        from_attributes = True