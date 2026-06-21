from datetime import datetime
from typing import Any

from pydantic import BaseModel


class WorkflowReplayChange(BaseModel):
    field: str
    before: Any
    after: Any


class WorkflowReplayResponse(BaseModel):
    replay_id: int
    source_workflow_run_id: int
    replay_workflow_run_id: int
    status: str
    changed: bool
    diff_summary: str
    changes: list[WorkflowReplayChange]
    created_at: datetime
