from datetime import datetime
from typing import List, Optional, Union

import uuid
from pydantic import BaseModel

from db.models import MouApplicationStatus
from db.models.mou_application import ModificationEntity
from schemas.document import DocumentRead
from schemas.mou_application import MouApplicationRead


class MouRead(BaseModel):
    uuid: uuid.UUID
    mou_application: MouApplicationRead
    documents: List[DocumentRead] = []

    class Config:
        from_attributes = True


class BasicMouReadApplication(BaseModel):
    uuid: uuid.UUID
    status: MouApplicationStatus
    reference_number: Optional[str] = None
    submitted_by: Optional[str] = None
    last_decision_date: Optional[datetime] = None
    modification_entity: Optional[List[Union[ModificationEntity, None]]] = None

    class Config:
        from_attributes = True

class BasicMouRead(BaseModel):
    uuid: uuid.UUID
    mou_application: BasicMouReadApplication

    class Config:
        from_attributes = True
