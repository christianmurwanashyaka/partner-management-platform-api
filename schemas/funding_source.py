from datetime import datetime
from pydantic import BaseModel
import uuid
from typing import Optional


class FundingSourceCreate(BaseModel):
    name: str
    description: Optional[str] = None


class FundingSourceRead(BaseModel):
    uuid: uuid.UUID
    name: str
    description: Optional[str] = None
    created_at: datetime
    created_by: str

    class Config:
        from_attributes = True
