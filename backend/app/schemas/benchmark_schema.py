from datetime import datetime

from pydantic import BaseModel


class BenchmarkRunHistoryResponse(BaseModel):
    id: int
    pass_rate: float
    average_quality_score: float
    created_at: datetime

    class Config:
        from_attributes = True
