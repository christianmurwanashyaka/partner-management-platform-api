from typing import List

import uuid
from pydantic import BaseModel

from schemas.party import PartyRead
from schemas.project import ProjectRead


class MouDetailCreate(BaseModel):
    project_id: uuid.UUID
    parties: List[uuid.UUID]

    class Config:
        from_attributes = True


class MouDetailRead(BaseModel):
    uuid: uuid.UUID
    project: ProjectRead
    parties: List[PartyRead]

    class Config:
        from_attributes = True
