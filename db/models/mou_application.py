from enum import Enum
from typing import List, Optional

import uuid
from sqlmodel import Field, Relationship

from db.models import CommonBaseModel


class MouApplicationStatus(str, Enum):
    PENDING = 'pending'
    UNDER_REVIEW = 'under_review'
    UNDER_APPROVAL = 'under_approval'
    APPROVED = 'approved'
    REJECTED = 'rejected'


class MouApplication(CommonBaseModel, table=True):
    __tablename__ = 'mou_application'

    status: MouApplicationStatus = Field(default=MouApplicationStatus.PENDING, description='Status of the MOU application')
    mou_detail_id: uuid.UUID = Field(default=uuid.UUID, foreign_key='mou_detail.uuid')
    mou_detail: 'MouDetail' = Relationship(back_populates='mou_application', sa_relationship_kwargs={'lazy': 'selectin'})
    approvals: List['MouApproval'] = Relationship(back_populates='mou_application', sa_relationship_kwargs={'lazy': 'selectin'})
    reviews: List['MouReview'] = Relationship(back_populates='mou_application', sa_relationship_kwargs={'lazy': 'selectin'})
    comments: List['MouComment'] = Relationship(back_populates='mou_application', sa_relationship_kwargs={'lazy': 'selectin'})
    documents: List['Document'] = Relationship(back_populates='mou_application', sa_relationship_kwargs={'lazy': 'selectin'})
    mou: Optional['Mou'] = Relationship(back_populates='mou_application', sa_relationship_kwargs={'lazy': 'selectin'})
