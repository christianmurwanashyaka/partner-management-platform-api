from enum import Enum
from typing import List, Optional

import uuid
from sqlmodel import Field, Relationship

from db.models import CommonBaseModel
from .user import MOHStaffLevel


class MouApplicationStatus(str, Enum):
    PENDING = 'pending'
    UNDER_REVIEW = 'under_review'
    UNDER_APPROVAL = 'under_approval'
    APPROVED = 'approved'
    REJECTED = 'rejected'
    REQUEST_MODIFICATION = 'request_modification'


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
    approval_or_review: List['MouApprovalOrReview'] = Relationship(back_populates='mou_application', sa_relationship_kwargs={'lazy': 'selectin'})
    current_reviewer_id: Optional[uuid.UUID] = Field(default=None, foreign_key='user.uuid',
                                                     description='Current reviewer of the MOU application')
    current_reviewer: Optional['User'] = Relationship(sa_relationship_kwargs={'lazy': 'selectin'})
    next_level: Optional[MOHStaffLevel] = Field(default=None, description='Next level for the MOU application')

    @property
    def reference_number(self) -> str:
        """Generate a unique reference number combining the creation date and the ID"""
        if not self.id or not self.created_at:
            return None
        return f"{self.created_at:%Y%m%d}-{self.id}"
