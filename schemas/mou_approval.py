from datetime import datetime
from typing import Optional

import uuid
from pydantic import BaseModel

from db.models import MOHStaffLevel
from schemas.mou_approval_or_review import UserProfileForApprovalOrReview, MouApprovalOrReviewBase


class MouApprovalCreate(MouApprovalOrReviewBase):
    pass


class MouApprovalCommentRead(BaseModel):
    uuid: uuid.UUID
    content: str
    created_at: datetime
    created_by: str

    class Config:
        from_attributes = True


class MouApprovalRead(MouApprovalOrReviewBase):
    uuid: uuid.UUID
    created_at: datetime
    created_by: str
    current_approver: Optional[UserProfileForApprovalOrReview] = None
    next_level: Optional[MOHStaffLevel] = None
