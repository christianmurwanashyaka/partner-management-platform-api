import uuid
from datetime import datetime

from pydantic import BaseModel


class ReportActivityCreate(BaseModel):
    activity_uuid: uuid.UUID
    executed_budget: float
    actual_start_date: datetime
    actual_end_date: datetime

    class Config:
        from_attributes = True
        