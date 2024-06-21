from typing import List, Optional

import uuid
from pydantic import BaseModel

from schemas.document import DocumentRead
from schemas.party import PartyRead
from schemas.project import ProjectRead, ProjectList


class MouDetailCreate(BaseModel):
    project_id: uuid.UUID
    parties: List[uuid.UUID]

    class Config:
        from_attributes = True


class MouDetailRead(BaseModel):
    uuid: uuid.UUID
    project: ProjectRead
    parties: List[PartyRead]
    documents: List[DocumentRead] = []

    class Config:
        from_attributes = True


class ApplicationMouDetailRead(BaseModel):
    uuid: uuid.UUID
    project: ProjectList
    parties: List[PartyRead]

    class Config:
        from_attributes = True


class ApplicationMouDetailReadWithActivities(BaseModel):
    uuid: uuid.UUID
    project: ProjectRead
    parties: List[PartyRead]

    class Config:
        from_attributes = True
