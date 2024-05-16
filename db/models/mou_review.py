from enum import Enum
from typing import List

import uuid
from sqlmodel import Field, Relationship

from db.models import CommonBaseModel


class MouReviewDecision(str, Enum):
    VERIFIED = 'verified'
    NOT_YET_VERIFIED = 'not_yet_verified'


class MouReview(CommonBaseModel, table=True):
    __tablename__ = 'mou_review'

    user_id: uuid.UUID = Field(foreign_key='user.uuid')
    user: 'User' = Relationship(sa_relationship_kwargs={'lazy': 'selectin'})

    mou_application_id: uuid.UUID = Field(foreign_key='mou_application.uuid')
    mou_application: 'MouApplication' = Relationship(back_populates='reviews', sa_relationship_kwargs={'lazy': 'selectin'})

    comments: List['MouComment'] = Relationship(back_populates='mou_review', sa_relationship_kwargs={'lazy': 'selectin'})

    decision: MouReviewDecision = Field(description='Decision made during the review')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.validate_decision()

    def validate_decision(self):
        from db.models.user import SwapTeamLevel
        if self.user.level not in [SwapTeamLevel.PARTNER_COORDINATOR, SwapTeamLevel.LEGAL_ADVISOR]:
            raise ValueError('Only Partner Coordinator or Legal Advisor can make review decisions')
