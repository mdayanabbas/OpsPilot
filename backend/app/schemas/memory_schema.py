from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class MemoryItemResponse(BaseModel):
    id: int
    workflow_run_id: int
    item_type: str
    title: str
    category: Optional[str]
    content: str
    relevance_score: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True
