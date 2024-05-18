from enum import Enum
from typing import Optional
import uuid
from pydantic import BaseModel
from datetime import datetime


class CombinedDecision(str, Enum):
    RECOMMEND_APPROVAL = 'recommend_approval'
    RECOMMEND_REJECTION = 'recommend_rejection'
    REQUEST_MODIFICATION = 'request_modification'
    APPROVE = 'approve'
    REJECT = 'reject'
    VERIFIED = 'verified'
    NOT_YET_VERIFIED = 'not_yet_verified'


class CombinedApprovalOrReviewRead(BaseModel):
    uuid: uuid.UUID
    created_at: datetime
    created_by: str
    decision: CombinedDecision
    comment: Optional[str] = None

    class Config:
        from_attributes = True
