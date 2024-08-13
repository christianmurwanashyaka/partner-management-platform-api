import uuid
from datetime import datetime
from typing import List

from sqlmodel import Field, Relationship

from db.models import CommonBaseModel


class Accomplishment(CommonBaseModel, table=True):
    description: str = Field(description="Description of the Accomplishment")
    report_activity_uuid: uuid.UUID = Field(default=uuid.UUID, foreign_key="report_activity.uuid", index=True)
    report_activity: 'ReportActivity' = Relationship(back_populates="accomplishments", sa_relationship_kwargs={'lazy': 'selectin'})
    accomplishment_date: datetime = Field(default=None, nullable=True, description="The date of the accomplishment")
    accomplished_by: str = Field(description="Name of the person who accomplished the Accomplishment")
    comments: List['Comment'] = Relationship(back_populates='accomplishment', sa_relationship_kwargs={'lazy': 'selectin'})