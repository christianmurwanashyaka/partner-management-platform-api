from typing import List

import uuid
from sqlmodel import Relationship, Field

from db.models import CommonBaseModel


class Mou(CommonBaseModel, table=True):
    __tablename__ = 'mou'

    mou_application_id: uuid.UUID = Field(foreign_key='mou_application.uuid', index=True)
    mou_application: 'MouApplication' = Relationship(back_populates='mou', sa_relationship_kwargs={'lazy': 'selectin'})

    documents: List['Document'] = Relationship(back_populates='mou', sa_relationship_kwargs={'lazy': 'selectin'})
