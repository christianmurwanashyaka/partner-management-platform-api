from datetime import datetime
from typing import Optional

import uuid
from pydantic import BaseModel

from db.models import MOHStaffLevel
from schemas.mou_approval_or_review import MouApprovalOrReviewBase, UserProfileForApprovalOrReview


class MouReviewCreate(MouApprovalOrReviewBase):
    pass


class MouReviewCommentRead(BaseModel):
    uuid: uuid.UUID
    content: str
    created_at: datetime
    created_by: str

    class Config:
        from_attributes = True


class MouReviewRead(MouApprovalOrReviewBase):
    uuid: uuid.UUID
    created_at: datetime
    created_by: str
    current_reviewer: Optional[UserProfileForApprovalOrReview]
    next_level: Optional[MOHStaffLevel] = None
