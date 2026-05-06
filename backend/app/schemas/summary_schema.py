from pydantic import BaseModel
from typing import Optional


class FounderSummaryResponse(BaseModel):
    id: int
    workflow_run_id: int
    summary: str
    risks: Optional[str]
    recommended_actions: Optional[str]

    class Config:
        from_attributes = True