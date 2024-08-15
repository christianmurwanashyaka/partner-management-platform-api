import datetime
from enum import Enum
from typing import List, Optional
import uuid
from sqlmodel import Field, Relationship
from db.models.base import CommonBaseModel


class ActivityStatus(str, Enum):
    NOT_STARTED = "not_started"
    ON_GOING = "on_going"
    COMPLETED = 'completed'


class ActivityReportingStatus(str, Enum):
    READY_FOR_REPORT = 'ready_for_report'
    REPORTED = 'reported'


class Activity(CommonBaseModel, table=True):
    __tablename__ = 'activity'

    project_id: uuid.UUID = Field(default=uuid.UUID, foreign_key='project.uuid', index=True)
    project: 'Project' = Relationship(back_populates='activities', sa_relationship_kwargs={'lazy': 'selectin'})

    start_date: datetime.date = Field(..., description="Start date of the project", index=True)
    end_date: datetime.date = Field(..., description="End date of the project", index=True)
    name: str = Field(..., description='Name of the activity', index=True)
    description: str | None = Field(default=None, nullable=True, description='Optional description of the activity')
    implementer: str = Field(..., description='Name of the implementer of the activity', index=True)
    implementer_unit: str = Field(..., description='Unit or group within the implementer organization', index=True)
    fiscal_year: str = Field(..., description='Fiscal year of the activity', index=True)

    domains: List['ActivityDomain'] = Relationship(back_populates='activity', sa_relationship_kwargs={'lazy': 'selectin'})
    input_details: List['InputDetail'] = Relationship(back_populates='activity', sa_relationship_kwargs={'lazy': 'selectin'})
    operational_zones: List['OperationalZone'] = Relationship(back_populates='activity', sa_relationship_kwargs={'lazy': 'selectin'})
    report_uuid: Optional[uuid.UUID] = Field(foreign_key='report.uuid', nullable=True, index=True)
    report: Optional['Report'] = Relationship(back_populates='activities', sa_relationship_kwargs={'lazy': 'selectin'})
    status: Optional[ActivityStatus] = Field(default=None, nullable=True, index=True)
    users: List['UserActivity'] = Relationship(back_populates='activity', sa_relationship_kwargs={'lazy': 'selectin'})
    report_status: Optional[ActivityReportingStatus] = Field(default=None, nullable=True, index=True)
