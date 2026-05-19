from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class AgentExecutionTraceResponse(BaseModel):
    id: int
    workflow_run_id: int
    planner_decision_id: int
    tool_name: str
    status: str
    result_summary: Optional[str]
    error_message: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True
