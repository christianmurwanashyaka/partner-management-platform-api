from datetime import datetime

import uuid
from pydantic import BaseModel
from typing import Optional, List

from schemas.sub_domain_function import SubDomainFunctionRead


class SubDomainList(BaseModel):
    uuid: uuid.UUID
    name: str
    description: Optional[str] = None
    created_at: datetime
    created_by: str
    domain_id: uuid.UUID

    class Config:
        from_attributes = True


class SubDomainRead(BaseModel):
    uuid: uuid.UUID
    name: str
    description: Optional[str] = None
    created_at: datetime
    created_by: str
    functions: List[SubDomainFunctionRead] = []
    domain_id: uuid.UUID

    class Config:
        from_attributes = True


class SubDomainCreate(BaseModel):
    name: str
    description: Optional[str] = None
    domain_uuid: uuid.UUID

    class Config:
        from_attributes = True
