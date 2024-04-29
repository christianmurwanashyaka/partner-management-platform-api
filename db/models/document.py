from enum import Enum
from typing import Optional

import uuid
from sqlmodel import Field, Relationship

from db.models.base import CommonBaseModel


class DocumentType(str, Enum):
    APPOINTMENT_LETTER = 'appointment_letter'
    NOTIFIED_CONSTITUTION_BYLAWS = 'notified_constitution_bylaws'


class Document(CommonBaseModel, table=True):
    __tablename__ = 'document'

    name: str
    description: Optional[str] = None
    document_type: DocumentType
    path: str
    filename: str
    registration: bool = Field(default=False)
    organization_id: Optional[uuid.UUID] = Field(default=None, foreign_key='organization.uuid')
    organization: Optional['Organization'] = Relationship(back_populates='documents', sa_relationship_kwargs={'lazy': 'selectin'})
