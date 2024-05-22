from datetime import datetime
from typing import List, Optional

import uuid
from pydantic import BaseModel, EmailStr

from db.models import MouApplicationStatus, MOHStaffLevel
from schemas.document import DocumentRead
from schemas.mou_approval_or_review import UserProfileForApprovalOrReview
from schemas.mou_detail import MouDetailRead, ApplicationMouDetailRead
from schemas.user import UserProfile


class MouApplicationCreate(BaseModel):
    mou_detail_id: uuid.UUID

    class Config:
        from_attributes = True


class MouApplicationBasicCommentRead(BaseModel):
    uuid: uuid.UUID
    content: str
    user: UserProfile
    created_at: datetime
    created_by: str

    class Config:
        from_attributes = True


class MouApplicationRead(BaseModel):
    uuid: uuid.UUID
    status: MouApplicationStatus
    mou_detail: MouDetailRead
    documents: List[DocumentRead] = []
    comments: List[MouApplicationBasicCommentRead] = []

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
    mou_detail: ApplicationMouDetailRead
    documents: List[DocumentRead] = []
    organization: SimpleOrganizationRead
    current_reviewer: Optional[UserProfileForApprovalOrReview] = None
    next_level: MOHStaffLevel

    class Config:
        from_attributes = True
