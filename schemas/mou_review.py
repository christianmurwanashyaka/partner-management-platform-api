from datetime import datetime
from typing import Optional

import uuid
from pydantic import BaseModel

from db.models.mou_review import MouReviewDecision


class MouReviewBase(BaseModel):
    decision: MouReviewDecision
    comment: Optional[str] = None


class MouReviewCreate(MouReviewBase):
    pass


class MouReviewRead(MouReviewBase):
    uuid: uuid.UUID
    created_at: datetime
    created_by: str
