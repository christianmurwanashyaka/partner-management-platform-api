from datetime import datetime
from typing import List

import uuid
from pydantic import BaseModel

from schemas.input import InputRead
from schemas.input_category import InputCategoryRead


class InputDetailCreate(BaseModel):
    input_category_id: uuid.UUID
    input_id: uuid.UUID
    budget: float
    districts: List[str]
    provinces: List[str]

    class Config:
        from_attributes = True


class InputDetailRead(BaseModel):
    uuid: uuid.UUID
    input_category: InputCategoryRead
    input: InputRead
    districts: List[str]
    provinces: List[str]
    budget: float
    created_at: datetime
    created_by: str

    class Config:
        from_attributes = True
