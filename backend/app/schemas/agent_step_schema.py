from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class AgentStepResponse(BaseModel):
    id: int
    workflow_run_id: int
    step_name: str
    status: str
    input_summary: Optional[str]
    output_summary: Optional[str]
    confidence: Optional[float]
    latency_ms: Optional[int]
    error_message: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True