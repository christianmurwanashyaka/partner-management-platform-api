from typing import List

import uuid
from pydantic import BaseModel

from schemas.document import DocumentRead
from schemas.mou_application import MouApplicationRead


class MouRead(BaseModel):
    uuid: uuid.UUID
    mou_application: MouApplicationRead
    documents: List[DocumentRead] = []

    class Config:
        from_attributes = True
        