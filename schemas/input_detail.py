from datetime import datetime

import uuid
from pydantic import BaseModel

from schemas.input import InputRead
from schemas.input_category import InputCategoryRead, InputCategoryList


class InputDetailCreate(BaseModel):
    input_category_id: uuid.UUID
    input_id: uuid.UUID
    budget: float
    district: str
    province: str

    class Config:
        from_attributes = True


class InputDetailUpdate(InputDetailCreate):

    class Config:
        from_attributes = True


class InputDetailRead(BaseModel):
    uuid: uuid.UUID
    input_category: InputCategoryRead
    input: InputRead
    province: str
    district: str
    budget: float
    created_at: datetime
    created_by: str

    class Config:
        from_attributes = True
