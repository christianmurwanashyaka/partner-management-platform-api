from datetime import datetime
from typing import Optional

import uuid
from pydantic import BaseModel

from db.models import MouApprovalDecision


class MouApprovalBase(BaseModel):
    decision: MouApprovalDecision
    comment: Optional[str] = None


class MouApprovalCreate(MouApprovalBase):
    pass


class MouApprovalRead(MouApprovalBase):
    uuid: uuid.UUID
    created_at: datetime
    created_by: str
