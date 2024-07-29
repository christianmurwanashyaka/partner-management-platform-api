from enum import Enum
from typing import List, Optional

import uuid
from sqlmodel import Field, Relationship

from db.models import CommonBaseModel


class MouReviewDecision(str, Enum):
    RECOMMEND_APPROVAL = 'recommend_approval'
    REQUEST_MODIFICATION = 'request_modification'
    REJECT = 'reject'
    VERIFIED = 'verified'


class MouReview(CommonBaseModel, table=True):
    __tablename__ = 'mou_review'
    
    decision: MouReviewDecision = Field(description='Decision made during the review')
    current_review_id: uuid.UUID = Field(foreign_key='user.uuid', index=True)
    current_reviewer: 'User' = Relationship(sa_relationship_kwargs={'lazy': 'selectin'})
    mou_application_id: uuid.UUID = Field(foreign_key='mou_application.uuid', index=True)
    mou_application: 'MouApplication' = Relationship(back_populates='reviews', sa_relationship_kwargs={'lazy': 'selectin'})
    comments: List['MouComment'] = Relationship(back_populates='mou_review', sa_relationship_kwargs={'lazy': 'selectin'})
    processing_time: Optional[int] = Field(
        default=None,
        description='Processing time from decision to decision'
    )