from datetime import datetime
from enum import Enum
from typing import List, Optional, Union

import uuid
from sqlmodel import Field, Relationship
from sqlalchemy import String, ARRAY, Column

from db.models import CommonBaseModel
from .user import MOHStaffLevel


class ModificationEntity(str, Enum):
    DOCUMENT = 'DOCUMENTS'
    PROJECT = 'PROJECT'
    ACTIVITIES = 'ACTIVITY'
    MOU = 'MoU'


class MouApplicationStatus(str, Enum):
    PENDING = 'pending'
    UNDER_REVIEW = 'under_review'
    READY_FOR_APPROVAL = 'ready_for_approval'
    UNDER_APPROVAL = 'under_approval'
    APPROVED = 'approved'
    REJECTED = 'rejected'
    REQUEST_MODIFICATION = 'request_modification'
    MODIFIED = "modified"


class MouApplication(CommonBaseModel, table=True):
    __tablename__ = 'mou_application'

    status: MouApplicationStatus = Field(default=MouApplicationStatus.PENDING, description='Status of the MOU application')
    mou_detail_id: uuid.UUID = Field(default=uuid.UUID, foreign_key='mou_detail.uuid', index=True)
    mou_detail: 'MouDetail' = Relationship(back_populates='mou_application', sa_relationship_kwargs={'lazy': 'noload'})
    approvals: List['MouApproval'] = Relationship(back_populates='mou_application', sa_relationship_kwargs={'lazy': 'noload'})
    reviews: List['MouReview'] = Relationship(back_populates='mou_application', sa_relationship_kwargs={'lazy': 'noload'})
    comments: List['MouComment'] = Relationship(back_populates='mou_application', sa_relationship_kwargs={'lazy': 'noload'})
    documents: List['Document'] = Relationship(back_populates='mou_application', sa_relationship_kwargs={'lazy': 'noload'})
    mou: Optional['Mou'] = Relationship(back_populates='mou_application', sa_relationship_kwargs={'lazy': 'noload'})
    approval_or_review: List['MouApprovalOrReview'] = Relationship(back_populates='mou_application', sa_relationship_kwargs={'lazy': 'noload'})
    current_reviewer_id: Optional[uuid.UUID] = Field(default=None, foreign_key='user.uuid',
                                                     description='Current reviewer of the MOU application', index=True)
    current_reviewer: Optional['User'] = Relationship(sa_relationship_kwargs={'lazy': 'noload'})
    next_level: Optional[MOHStaffLevel] = Field(default=None, description='Next level for the MOU application', index=True)
    created_by: Optional[str] = Field(default=None, description='Email of the user who created the MOU application', index=True)
    submitted_by: Optional[str] = Field(default=None, description='Name of the user who submitted the MOU application')
    last_decision_date: Optional[datetime] = Field(
        default=None,
        description='Date of the last decision made on the MOU application'
    )
    modification_entity: Optional[List[Union[ModificationEntity, None]]] = Field(default=None, sa_column=Column(ARRAY(String)), description='Entities that need modification if requested')
    partner_template_comment: Optional[str] = Field(default=None, description='Partner template comment')
    report: Optional['Report'] = Relationship(back_populates='mou_application', sa_relationship_kwargs={'lazy': 'noload'})

    @property
    def reference_number(self) -> str:
        """Generate a unique reference number combining the creation date and the ID"""
        if not self.id or not self.created_at:
            return None
        return f"{self.created_at:%Y%m%d}-{self.id}"
