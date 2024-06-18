from datetime import datetime
from enum import Enum
from typing import Optional, List

import uuid
from pydantic import BaseModel, EmailStr

from db.models import UserRole, MOHStaffLevel
from db.models.mou_application import ModificationEntity
from db.models.mou_approval_or_review import MouApprovalOrReviewDecision


class UserProfileForApprovalOrReview(BaseModel):
    uuid: uuid.UUID
    first_name: str
    last_name: str
    email: EmailStr
    role: UserRole
    level: Optional[MOHStaffLevel] = None

    class Config:
        from_attributes = True


class MouApprovalOrReviewBase(BaseModel):
    decision: MouApprovalOrReviewDecision
    comment: Optional[str] = None


class MouApprovalOrReviewCreate(MouApprovalOrReviewBase):
    pass


class MouApprovalOrReviewCommentRead(BaseModel):
    uuid: uuid.UUID
    content: str
    created_at: datetime
    created_by: str

    class Config:
        from_attributes = True


class MouApprovalOrReviewRead(MouApprovalOrReviewBase):
    uuid: uuid.UUID
    created_at: datetime
    current_reviewer: Optional[UserProfileForApprovalOrReview]
    next_level: Optional[MOHStaffLevel] = None
