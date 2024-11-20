from datetime import datetime
from typing import Optional, List

import uuid
from pydantic import BaseModel

from schemas.sub_financing_scheme import SubFinancingSchemeList


class FinancingSchemeCreate(BaseModel):
    name: str
    description: Optional[str] = None
    sha_code: str

    class Config:
        from_attributes = True


class FinancingSchemeList(BaseModel):
    uuid: uuid.UUID
    name: str
    description: Optional[str] = None
    created_at: datetime
    created_by: str
    sha_code: str

    class Config:
        from_attributes = True


class FinancingSchemeRead(BaseModel):
    uuid: uuid.UUID
    name: str
    sha_code: str
    description: Optional[str] = None
    sub_financing_schemes: List[SubFinancingSchemeList] = []
    created_at: datetime
    created_by: str

    class Config:
        from_attributes = True
