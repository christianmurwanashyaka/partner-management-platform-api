from typing import List, Optional

import uuid
from sqlmodel import Field, Relationship
from sqlalchemy import String, ARRAY, Column

from db.models import CommonBaseModel


class Party(CommonBaseModel, table=True):
    __tablename__ = 'party'

    name: str = Field(..., description='Name of the party', index=True)
    responsibilities: List[str] = Field(sa_column=Column(ARRAY(String)), description='List of responsibilities for the party')
    organization_id: Optional[uuid.UUID] = Field(default=None, foreign_key='organization.uuid', index=True)
    organization: Optional['Organization'] = Relationship(back_populates='parties', sa_relationship_kwargs={'lazy': 'selectin'})
    signatory: str = Field(..., description='Signatory of the party')
    mou_detail_id: Optional[uuid.UUID] = Field(default=None, foreign_key='mou_detail.uuid', index=True)
    mou_detail: Optional['MouDetail'] = Relationship(back_populates='parties', sa_relationship_kwargs={'lazy': 'selectin'})
    position: str = Field(default='CEO', description='Position of the signatory')
    duration: Optional[str] = Field(default=None, description="The duration of the mou")
    reason_for_extended_duration: Optional[str] = Field(default=None, description="Reason why duration is more than 1 year")