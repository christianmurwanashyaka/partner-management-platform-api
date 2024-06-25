import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class SubFunctionCreate(BaseModel):
    name: str
    description: Optional[str] = None
    function_uuid: uuid.UUID

    class Config:
        from_attributes = True


class SubFunctionRead(BaseModel):
    uuid: uuid.UUID
    name: str
    description: Optional[str] = None
    created_at: datetime
    created_by: str
    function_id: uuid.UUID

    class Config:
        from_attributes = True
