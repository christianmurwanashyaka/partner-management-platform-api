from enum import Enum
from typing import List

import uuid
from sqlmodel import Field, Relationship

from .base import CommonBaseModel
from .user import MOHStaffLevel


class MouApprovalDecision(str, Enum):
    RECOMMEND_APPROVAL = 'recommend_approval'
    RECOMMEND_REJECTION = 'recommend_rejection'
    REQUEST_MODIFICATION = 'request_modification'
    APPROVE = 'approve'
    REJECT = 'reject'


class MouApproval(CommonBaseModel, table=True):
    __tablename__ = 'mou_approval'
    decision: MouApprovalDecision = Field(description='Decision made on the MOU Application')
    approver_id: uuid.UUID = Field(foreign_key='user.uuid')
    approver: 'User' = Relationship(sa_relationship_kwargs={'lazy': 'selectin'})
    mou_application_id: uuid.UUID = Field(foreign_key='mou_application.uuid')
    mou_application: 'MouApplication' = Relationship(back_populates='approvals', sa_relationship_kwargs={'lazy': 'selectin'})
    comments: List['MouComment'] = Relationship(back_populates='mou_approval', sa_relationship_kwargs={'lazy': 'selectin'})
