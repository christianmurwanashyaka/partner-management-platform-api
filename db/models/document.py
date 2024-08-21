from enum import Enum
from typing import Optional

import uuid
from sqlmodel import Field, Relationship

from db.models.base import CommonBaseModel


class DocumentType(str, Enum):
    APPOINTMENT_LETTER = 'appointment_letter'
    NOTIFIED_CONSTITUTION_BYLAWS = 'notified_constitution_bylaws'
    CAPACITY_BUILDING_TRANSFER_PLAN = 'capacity_building_transfer_plan'
    MEMO_DESCRIBING_THE_SOURCE_OF_FUNDS = 'memo_describing_the_source_of_funds'
    MEMO_DESCRIBING_THE_LONG_TERM_OBJECTIVES = 'memo_describing_the_long_term_objectives'
    STRATEGIC_PLAN = 'strategic_plan'
    ADDITIONAL_DOCUMENT = 'additional_document'
    ACTION_PLAN = 'action_plan'
    MOU = 'mou'


class Document(CommonBaseModel, table=True):
    __tablename__ = 'document'

    name: str
    description: Optional[str] = None
    document_type: DocumentType
    path: str
    filename: str
    registration: bool = Field(default=False)
    organization_id: Optional[uuid.UUID] = Field(default=None, foreign_key='organization.uuid', index=True)
    organization: Optional['Organization'] = Relationship(back_populates='documents', sa_relationship_kwargs={'lazy': 'noload'})
    mou_detail_id: Optional[uuid.UUID] = Field(default=None, foreign_key='mou_detail.uuid', index=True)
    mou_detail: Optional['MouDetail'] = Relationship(back_populates='documents', sa_relationship_kwargs={'lazy': 'noload'})
    mou_application_id: Optional[uuid.UUID] = Field(default=None, foreign_key='mou_application.uuid', index=True)
    mou_application: Optional['MouApplication'] = Relationship(back_populates='documents', sa_relationship_kwargs={'lazy': 'noload'})
    mou_id: Optional[uuid.UUID] = Field(default=None, foreign_key='mou.uuid', index=True)
    mou: Optional['Mou'] = Relationship(back_populates='documents', sa_relationship_kwargs={'lazy': 'noload'})

