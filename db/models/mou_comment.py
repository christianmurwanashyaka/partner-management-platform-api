from typing import Optional

import uuid
from sqlmodel import Relationship, Field

from db.models import CommonBaseModel


class MouComment(CommonBaseModel, table=True):
    __tablename__ = 'mou_comment'

    content: str = Field(description='Content of the comment')
    user_id: uuid.UUID = Field(foreign_key='user.uuid', index=True)
    user: 'User' = Relationship(sa_relationship_kwargs={'lazy': 'selectin'})

    mou_application_id: uuid.UUID = Field(foreign_key='mou_application.uuid', index=True)
    mou_application: 'MouApplication' = Relationship(back_populates='comments', sa_relationship_kwargs={'lazy': 'selectin'})

    mou_approval_id: Optional[uuid.UUID] = Field(foreign_key='mou_approval.uuid', nullable=True, index=True)
    mou_approval: Optional['MouApproval'] = Relationship(back_populates='comments', sa_relationship_kwargs={'lazy': 'selectin'})

    mou_review_id: Optional[uuid.UUID] = Field(foreign_key='mou_review.uuid', nullable=True, index=True)
    mou_review: Optional['MouReview'] = Relationship(back_populates='comments', sa_relationship_kwargs={'lazy': 'selectin'})

    mou_approval_or_review_id: Optional[uuid.UUID] = Field(foreign_key='mou_approval_or_review.uuid', nullable=True, index=True)
    mou_approval_or_review: Optional['MouApprovalOrReview'] = Relationship(back_populates='comments', sa_relationship_kwargs={'lazy': 'selectin'})
