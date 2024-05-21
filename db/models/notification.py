import uuid

from pydantic import EmailStr
from sqlmodel import Field, Relationship
import sqlalchemy as sa

from db.models import CommonBaseModel


class Notification(CommonBaseModel, table=True):
    __tablename__ = 'notification'

    recipient_id: uuid.UUID = Field(default=uuid.UUID, foreign_key='user.uuid')
    recipient: 'User' = Relationship(back_populates='notifications', sa_relationship_kwargs={'lazy': 'selectin'})
    subject: str = Field(..., description='Subject of the notification')
    from_email: EmailStr = Field(sa_column=sa.Column(sa.String))
    is_read: bool = Field(default=False, description='Read status of the notification')
    message: str = Field(..., description='Message content of the notification')
