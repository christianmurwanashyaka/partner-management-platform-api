from typing import List

import uuid
from sqlmodel import Field, Relationship

from db.models import CommonBaseModel


class MouReview(CommonBaseModel, table=True):
    __tablename__ = 'mou_review'

    user_id: uuid.UUID = Field(foreign_key='user.uuid')
    user: 'User' = Relationship(sa_relationship_kwargs={'lazy': 'selectin'})

    mou_application_id: uuid.UUID = Field(foreign_key='mou_application.uuid')
    mou_application: 'MouApplication' = Relationship(back_populates='reviews', sa_relationship_kwargs={'lazy': 'selectin'})

    comments: List['MouComment'] = Relationship(back_populates='mou_review', sa_relationship_kwargs={'lazy': 'selectin'})
