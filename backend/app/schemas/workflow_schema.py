from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class WorkflowRunCreate(BaseModel):
    input_text: str = Field(..., min_length=10)


class WorkflowRunResponse(BaseModel):
    id: int
    input_text: str
    status: str
    workflow_type: str
    confidence: Optional[float]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True