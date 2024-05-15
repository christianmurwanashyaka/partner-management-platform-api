import datetime
from typing import List
import uuid
from sqlmodel import Field, Relationship
from db.models.base import CommonBaseModel


class Activity(CommonBaseModel, table=True):
    __tablename__ = 'activity'

    project_id: uuid.UUID = Field(default=uuid.UUID, foreign_key='project.uuid')
    project: 'Project' = Relationship(back_populates='activities', sa_relationship_kwargs={'lazy': 'selectin'})

    start_date: datetime.date = Field(..., description="Start date of the project")
    end_date: datetime.date = Field(..., description="End date of the project")
    name: str = Field(..., description='Name of the activity')
    description: str | None = Field(default=None, nullable=True, description='Optional description of the activity')
    implementer: str = Field(..., description='Name of the implementer of the activity')
    implementer_unit: str = Field(..., description='Unit or group within the implementer organization')
    fiscal_year: str = Field(..., description='Fiscal year of the activity')

    domains: List['ActivityDomain'] = Relationship(back_populates='activity', sa_relationship_kwargs={'lazy': 'selectin'})
    input_details: List['InputDetail'] = Relationship(back_populates='activity', sa_relationship_kwargs={'lazy': 'selectin'})
    operational_zones: List['OperationalZone'] = Relationship(back_populates='activity', sa_relationship_kwargs={'lazy': 'selectin'})
