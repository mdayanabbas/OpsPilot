from datetime import datetime

from pydantic import BaseModel


class IncidentExecutionTraceResponse(BaseModel):
    id: int
    incident_id: int
    response_plan_id: int
    tool_name: str
    status: str
    result_summary: str | None
    error_message: str | None
    created_at: datetime

    class Config:
        from_attributes = True
