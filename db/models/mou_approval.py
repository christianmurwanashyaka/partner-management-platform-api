from enum import Enum
from typing import List, Optional

import uuid
from sqlmodel import Field, Relationship

from .base import CommonBaseModel


class MouApprovalDecision(str, Enum):
    APPROVE = 'approve'
    REQUEST_MODIFICATION = 'request_modification'
    REJECT = 'reject'


class MouApproval(CommonBaseModel, table=True):
    __tablename__ = 'mou_approval'

    decision: MouApprovalDecision = Field(description='Decision made on the MOU Application')
    current_approver_id: uuid.UUID = Field(foreign_key='user.uuid')
    current_approver: 'User' = Relationship(sa_relationship_kwargs={'lazy': 'selectin'})
    mou_application_id: uuid.UUID = Field(foreign_key='mou_application.uuid')
    mou_application: 'MouApplication' = Relationship(back_populates='approvals', sa_relationship_kwargs={'lazy': 'selectin'})
    comments: List['MouComment'] = Relationship(back_populates='mou_approval', sa_relationship_kwargs={'lazy': 'selectin'})
    processing_time: Optional[int] = Field(
        default=None,
        description='Processing time from decision to decision'
    )
