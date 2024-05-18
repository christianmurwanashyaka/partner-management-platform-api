from datetime import datetime
from typing import Optional

import uuid
from pydantic import BaseModel

from db.models.mou_approval_or_review import MouApprovalOrReviewDecision


class MouApprovalOrReviewBase(BaseModel):
    decision: MouApprovalOrReviewDecision
    comment: Optional[str] = None


class MouApprovalOrReviewCreate(MouApprovalOrReviewBase):
    pass


class MouApprovalOrReviewRead(MouApprovalOrReviewBase):
    uuid: uuid.UUID
    created_at: datetime
    created_by: str
