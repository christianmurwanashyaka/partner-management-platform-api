from datetime import datetime
from typing import List, Optional, Union

import uuid
from pydantic import BaseModel, EmailStr

from db.models import MouApplicationStatus, MOHStaffLevel
from db.models.mou_application import ModificationEntity
from schemas.document import DocumentRead
from schemas.mou_approval_or_review import UserProfileForApprovalOrReview
from schemas.mou_detail import MouDetailRead, ApplicationMouDetailRead, ApplicationMouDetailReadWithActivities
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


class SimpleOrganizationRead(BaseModel):
    uuid: uuid.UUID
    name: str
    email: EmailStr
    website: str
    organization_type: str

    class Config:
        from_attributes = True


class MouApplicationRead(BaseModel):
    uuid: uuid.UUID
    status: MouApplicationStatus
    mou_detail: MouDetailRead
    documents: List[DocumentRead] = []
    comments: List[MouApplicationBasicCommentRead] = []
    reference_number: Optional[str] = None
    submitted_by: Optional[str] = None
    last_decision_date: Optional[datetime] = None
    modification_entity: Optional[List[Union[ModificationEntity, None]]] = None
    organization: Optional[SimpleOrganizationRead] = None

    class Config:
        from_attributes = True


class MouApplicationOrganizationRead(BaseModel):
    created_at: datetime
    submitted_by: Optional[str] = None
    reference_number: Optional[str] = None
    uuid: uuid.UUID
    status: MouApplicationStatus
    organization: str
    organization_type: str
    next_level: Optional[MOHStaffLevel] = None

    class Config:
        from_attributes = True


class MouApplicationProjectRead(BaseModel):
    uuid: uuid.UUID
    reference_number: str
    project_name: str
    status: MouApplicationStatus
    comment: Optional[str] = None

    class Config:
        from_attributes = True
