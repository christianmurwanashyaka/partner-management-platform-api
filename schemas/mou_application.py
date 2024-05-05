from typing import List

import uuid
from pydantic import BaseModel

from db.models import MouApplicationStatus
from schemas.document import DocumentRead
from schemas.mou_detail import MouDetailRead


class MouApplicationCreate(BaseModel):
    mou_detail_id: uuid.UUID

    class Config:
        from_attributes = True


# TODO: ADD APPROVALS, COMMENTS AND REVIEWS FIELDS
class MouApplicationRead(BaseModel):
    uuid: uuid.UUID
    status: MouApplicationStatus
    mou_detail: MouDetailRead
    documents: List[DocumentRead] = []

    class Config:
        from_attributes = True
