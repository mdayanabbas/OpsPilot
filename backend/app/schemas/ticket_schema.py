from pydantic import BaseModel
from typing import Optional


class TicketResponse(BaseModel):
    id: int
    workflow_run_id: int
    title: str
    priority: str
    team: Optional[str]
    category: Optional[str]
    description: str
    acceptance_criteria: Optional[str]
    source_evidence: Optional[str]
    requires_approval: bool
    status: str

    class Config:
        from_attributes = True