from datetime import datetime

from pydantic import BaseModel


class IncidentResponsePlanResponse(BaseModel):
    id: int
    incident_id: int
    plan_type: str
    next_tools: list[str]
    reasoning: str
    created_at: datetime
