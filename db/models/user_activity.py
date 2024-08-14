import uuid

from sqlmodel import Field, Relationship

from db.models import CommonBaseModel


class UserActivity(CommonBaseModel, table=True):
    __tablename__ = 'user_activity'

    user_uuid: uuid.UUID = Field(default=uuid.UUID, foreign_key='user.uuid', index=True)
    user: 'User' = Relationship(back_populates='activities', sa_relationship_kwargs={'lazy': 'selectin'})
    activity_uuid: uuid.UUID = Field(default=uuid.UUID, foreign_key='activity.uuid', index=True)
    activity: 'Activity' = Relationship(back_populates='users', sa_relationship_kwargs={'lazy': 'selectin'})