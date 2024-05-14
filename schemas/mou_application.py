from typing import List

import uuid
from pydantic import BaseModel, EmailStr

from db.models import MouApplicationStatus
from schemas.document import DocumentRead
from schemas.mou_detail import MouDetailRead


class MouApplicationCreate(BaseModel):
    mou_detail_id: uuid.UUID

    class Config:
        from_attributes = True


# TODO: ADD APPROVALS, COMMENTS AND REVIEWS FIELDS
class MouApplicationRead(BaseModel):
    uuid: uuid.UUID
    status: MouApplicationStatus
    mou_detail: MouDetailRead
    documents: List[DocumentRead] = []

    class Config:
        from_attributes = True


class SimpleOrganizationRead(BaseModel):
    uuid: uuid.UUID
    name: str
    email: EmailStr
    website: str

    class Config:
        from_attributes = True


class MouApplicationOrganizationRead(BaseModel):
    uuid: uuid.UUID
    status: MouApplicationStatus
    mou_detail: MouDetailRead
    documents: List[DocumentRead] = []
    organization: SimpleOrganizationRead

    class Config:
        from_attributes = True
