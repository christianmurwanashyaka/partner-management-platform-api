from enum import Enum
from typing import List

import uuid
from sqlmodel import Field, Relationship

from .base import CommonBaseModel
from .user import SwapTeamLevel


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

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.validate_decision()

    def validate_decision(self):
        if self.approver.role == SwapTeamLevel.PARTNER_COORDINATOR:
            if self.decision not in [MouApprovalDecision.RECOMMEND_APPROVAL, MouApprovalDecision.RECOMMEND_REJECTION]:
                raise ValueError('The decision must be either RECOMMEND_APPROVAL or RECOMMEND_REJECTION')
        elif self.approver.role == SwapTeamLevel.TECHNICAL_DEPARTMENT:
            raise ValueError(f'Technical department cannot make approval decisions')
        elif self.approver.role in [SwapTeamLevel.LEGAL_ADVISOR, SwapTeamLevel.HOD, SwapTeamLevel.PS]:
            if self.decision not in [MouApprovalDecision.RECOMMEND_APPROVAL, MouApprovalDecision.RECOMMEND_REJECTION, MouApprovalDecision.REQUEST_MODIFICATION]:
                raise ValueError(f"{self.approver.role} can only recommend for approval, recommend for rejection, or request modification.")
        elif self.approver.role in [SwapTeamLevel.MINISTER_OF_STATE, SwapTeamLevel.MINISTER]:
            if self.decision not in [MouApprovalDecision.APPROVE, MouApprovalDecision.REJECT]:
                raise ValueError(f"{self.approver.role} can only approve or reject.")
