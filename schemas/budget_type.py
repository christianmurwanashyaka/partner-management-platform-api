from datetime import datetime
from pydantic import BaseModel
import uuid
from typing import Optional


class BudgetTypeCreate(BaseModel):
    name: str
    description: Optional[str] = None


class BudgetTypeRead(BaseModel):
    uuid: uuid.UUID
    name: str
    description: Optional[str] = None
    created_at: datetime
    created_by: str

    class Config:
        from_attributes = True
