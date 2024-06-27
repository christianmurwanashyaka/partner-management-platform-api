import uuid
from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel

from schemas.sub_function import SubFunctionRead


class SubDomainFunctionCreate(BaseModel):
    name: str
    description: Optional[str] = None
    sub_domain_uuid: uuid.UUID

    class Config:
        from_attributes = True


class SubDomainFunctionRead(BaseModel):
    uuid: uuid.UUID
    name: str
    description: Optional[str] = None
    sub_functions: List[SubFunctionRead] = []
    created_at: datetime
    created_by: str
    sub_domain_id: uuid.UUID

    class Config:
        from_attributes = True
