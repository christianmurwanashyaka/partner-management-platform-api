from datetime import datetime
from typing import Optional

import uuid
from pydantic import BaseModel

from db.models import MOHStaffLevel, MouReviewDecision
from schemas.mou_approval_or_review import UserProfileForApprovalOrReview


class MouReviewBase(BaseModel):
    decision: MouReviewDecision
    comment: Optional[str] = None


class MouReviewCreate(MouReviewBase):
    pass


class MouReviewCommentRead(BaseModel):
    uuid: uuid.UUID
    content: str
    created_at: datetime
    created_by: str

    class Config:
        from_attributes = True


class MouReviewRead(MouReviewBase):
    uuid: uuid.UUID
    created_at: datetime
    current_reviewer: Optional[UserProfileForApprovalOrReview]
    next_level: Optional[MOHStaffLevel] = None
