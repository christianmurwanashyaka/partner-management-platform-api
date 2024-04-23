from datetime import datetime

import uuid
from pydantic import BaseModel
from typing import Optional


class InputRead(BaseModel):
    uuid: uuid.UUID
    name: str
    description: Optional[str] = None
    created_at: datetime
    created_by: str
    category_id: uuid.UUID

    class Config:
        from_attributes = True


class InputCreate(BaseModel):
    name: str
    description: Optional[str] = None
    input_category_uuid: uuid.UUID

    class Config:
        from_attributes = True
