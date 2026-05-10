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
    created_at: datetime

    class Config:
        from_attributes = True
