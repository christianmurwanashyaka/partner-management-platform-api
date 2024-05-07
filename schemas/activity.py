from datetime import datetime
from typing import List, Optional

import uuid
from pydantic import BaseModel

from schemas.input_detail import InputDetailCreate, InputDetailRead
from schemas.sub_domain import SubDomainRead


class ActivityCreate(BaseModel):
    project_id: uuid.UUID
    description: Optional[str] = None
    name: str
    implementer: str
    implementer_unit: str
    fiscal_year: str
    sub_domain_id: uuid.UUID
    input_details: List[InputDetailCreate]

    class Config:
        from_attributes = True


class ActivityList(BaseModel):
    uuid: uuid.UUID
    project_id: uuid.UUID
    name: str
    implementer: str
    implementer_unit: str
    fiscal_year: str
    input_details: List[InputDetailRead]

    class Config:
        from_attributes = True


class ActivityRead(BaseModel):
    uuid: uuid.UUID
    project_id: uuid.UUID
    name: str
    description: Optional[str] = None
    implementer: str
    implementer_unit: str
    fiscal_year: str
    sub_domain: SubDomainRead
    created_at: datetime
    created_by: str

    class Config:
        from_attributes = True
