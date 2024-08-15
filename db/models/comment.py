import uuid
from typing import Optional

from sqlmodel import Field, Relationship

from db.models import CommonBaseModel


class Comment(CommonBaseModel, table=True):
    __tablename__ = 'comment'

    content: str = Field(description='Content of the comment')
    user_uuid: uuid.UUID = Field(foreign_key='user.uuid', index=True)
    user: 'User' = Relationship(sa_relationship_kwargs={'lazy': 'selectin'})

    report_uuid: Optional[uuid.UUID] = Field(foreign_key='report.uuid', nullable=True, index=True)
    report: Optional['Report'] = Relationship(back_populates='comments', sa_relationship_kwargs={'lazy': 'selectin'})

    report_activity_uuid: Optional[uuid.UUID] = Field(foreign_key='report_activity.uuid', nullable=True, index=True)
    report_activity: Optional['ReportActivity'] = Relationship(back_populates='comments', sa_relationship_kwargs={'lazy': 'selectin'})