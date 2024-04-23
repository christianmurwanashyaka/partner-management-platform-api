from datetime import datetime

import uuid
from pydantic import BaseModel
from typing import Optional, List

from schemas.sub_domain import SubDomainRead


class DomainInterventionCreate(BaseModel):
    name: str
    description: Optional[str] = None

    class Config:
        from_attributes = True


class DomainInterventionList(BaseModel):
    uuid: uuid.UUID
    name: str
    description: Optional[str] = None
    created_at: datetime
    created_by: str

    class Config:
        from_attributes = True


class DomainInterventionRead(BaseModel):
    uuid: uuid.UUID
    name: str
    description: Optional[str] = None
    subdomains: List[SubDomainRead] = []
    created_at: datetime
    created_by: str

    class Config:
        from_attributes = True
