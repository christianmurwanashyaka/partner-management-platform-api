from enum import Enum
from typing import List, Optional
import uuid
from sqlmodel import Field, Relationship, SQLModel

from db.models import CommonBaseModel


class MouApprovalOrReviewDecision(str, Enum):
    RECOMMEND_APPROVAL = 'recommend_approval'
    RECOMMEND_REJECTION = 'recommend_rejection'
    REQUEST_MODIFICATION = 'request_modification'
    APPROVE = 'approve'
    REJECT = 'reject'
    VERIFIED = 'verified'


class MouApprovalOrReview(CommonBaseModel, table=True):
    __tablename__ = 'mou_approval_or_review'

    mou_application_id: uuid.UUID = Field(foreign_key='mou_application.uuid', index=True)
    mou_application: 'MouApplication' = Relationship(back_populates='approval_or_review')
    decision: MouApprovalOrReviewDecision = Field(description='Decision made on the MOU Application')
    comments: List['MouComment'] = Relationship(back_populates='mou_approval_or_review', sa_relationship_kwargs={'lazy': 'selectin'})
    current_reviewer_id: Optional[uuid.UUID] = Field(foreign_key='user.uuid', description='Current reviewer of the MOU application', index=True)
    current_reviewer: Optional['User'] = Relationship(sa_relationship_kwargs={'lazy': 'selectin'})
