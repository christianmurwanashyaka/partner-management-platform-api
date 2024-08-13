import uuid
from datetime import datetime
from enum import Enum
from typing import List

from sqlmodel import Field, Relationship

from db.models import CommonBaseModel


class ReportStatus(str, Enum):
    PENDING = 'pending'
    REPORTED = 'reported'
    APPROVED = 'approved'


class Report(CommonBaseModel, table=True):
    __tablename__ = 'report'

    mou_application_uuid: uuid.UUID = Field(default=uuid.UUID, foreign_key='mou_application.uuid', index=True)
    mou_application: 'MouApplication' = Relationship(back_populates='report', sa_relationship_kwargs={'lazy': 'selectin'})
    reported_by: str = Field(description='Name of the user who submitted the report')
    organization_uuid: uuid.UUID = Field(default=uuid.UUID, foreign_key='organization.uuid', index=True)
    organization: 'Organization' = Relationship(back_populates='reports', sa_relationship_kwargs={'lazy': 'selectin'})
    reported_at: datetime = Field(description='Date and time of the report')
    project_uuid: uuid.UUID = Field(default=uuid.UUID, foreign_key='project.uuid', index=True)
    project: 'Project' = Relationship(back_populates='report', sa_relationship_kwargs={'lazy': 'selectin'})
    comments: List['Comment'] = Relationship(back_populates='report_activity', sa_relationship_kwargs={'lazy': 'selectin'})
    status: ReportStatus = Field(default=ReportStatus.PENDING, description='Status of the report')
    activities: List['Activity'] = Relationship(back_populates='report', sa_relationship_kwargs={'lazy': 'selectin'})
