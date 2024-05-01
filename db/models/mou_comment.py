import uuid
from sqlmodel import Relationship, Field

from db.models import CommonBaseModel


class MouComment(CommonBaseModel, table=True):
    __tablename__ = 'mou_comment'

    content: str = Field(description='Content of the comment')
    user_id: uuid.UUID = Field(foreign_key='user.uuid')
    user: 'User' = Relationship(sa_relationship_kwargs={'lazy': 'selectin'})

    mou_application_id: uuid.UUID = Field(foreign_key='mou_application.uuid')
    mou_application: 'MouApplication' = Relationship(back_populates='comments', sa_relationship_kwargs={'lazy': 'selectin'})

    mou_approval_id: uuid.UUID = Field(foreign_key='mou_approval.uuid')
    mou_approval: 'MouApproval' = Relationship(back_populates='comments', sa_relationship_kwargs={'lazy': 'selectin'})

    mou_review_id: uuid.UUID = Field(foreign_key='mou_review.uuid')
    mou_review: 'MouReview' = Relationship(back_populates='comments', sa_relationship_kwargs={'lazy': 'selectin'})