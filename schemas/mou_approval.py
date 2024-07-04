from datetime import datetime
from typing import Optional

import uuid
from pydantic import BaseModel

from db.models import MOHStaffLevel, MouApprovalDecision
from schemas.mou_approval_or_review import UserProfileForApprovalOrReview, MouApprovalOrReviewBase


class MouApprovalBase(BaseModel):
    decision: MouApprovalDecision
    comment: Optional[str] = None


class MouApprovalCreate(MouApprovalBase):
    pass


class MouApprovalCommentRead(BaseModel):
    uuid: uuid.UUID
    content: str
    created_at: datetime
    created_by: str

    class Config:
        from_attributes = True


class MouApprovalRead(MouApprovalBase):
    uuid: uuid.UUID
    created_at: datetime
    current_approver: Optional[UserProfileForApprovalOrReview] = None
    next_level: Optional[MOHStaffLevel] = None
    last_decision_date: Optional[datetime] = None
