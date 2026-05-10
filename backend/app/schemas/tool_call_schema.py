from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ToolCallResponse(BaseModel):
    id: int
    workflow_run_id: int
    step_name: str
    tool_name: str
    provider: str = "gemini"
    status: str
    attempt: int
    latency_ms: Optional[int]
    error_message: Optional[str]
    fallback_used: bool
    created_at: datetime

    class Config:
        from_attributes = True
