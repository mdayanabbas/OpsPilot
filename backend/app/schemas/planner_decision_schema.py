from datetime import datetime
from typing import Any

from pydantic import BaseModel


class PlannerDecisionResponse(BaseModel):
    id: int
    workflow_run_id: int
    plan_type: str
    next_tools: list[dict[str, Any]]
    requires_human_approval: bool
    reasoning_summary: str
    created_at: datetime
