from datetime import datetime

import uuid
from pydantic import BaseModel
from typing import Optional, List

from schemas.input import InputRead


class InputCategoryCreate(BaseModel):
    name: str
    description: Optional[str] = None

    class Config:
        from_attributes = True


class InputCategoryList(BaseModel):
    uuid: uuid.UUID
    name: str
    description: Optional[str] = None
    created_at: datetime
    created_by: str

    class Config:
        from_attributes = True


class InputCategoryRead(BaseModel):
    uuid: uuid.UUID
    name: str
    description: Optional[str] = None
    inputs: List[InputRead] = []
    created_at: datetime
    created_by: str

    class Config:
        from_attributes = True
