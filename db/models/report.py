import uuid
from datetime import datetime
from enum import Enum
from typing import List, Optional

from sqlmodel import Field, Relationship

from db.models import CommonBaseModel


class ReportStatus(str, Enum):
    PENDING = 'pending'
    REPORTED = 'reported'
    APPROVED = 'approved'


class Report(CommonBaseModel, table=True):
    __tablename__ = 'report'

    mou_application_uuid: uuid.UUID = Field(default=uuid.UUID, foreign_key='mou_application.uuid', index=True)
    mou_application: 'MouApplication' = Relationship(back_populates='report', sa_relationship_kwargs={'lazy': 'noload'})
    reported_by: Optional[str] = Field(default=None, nullable=True, description='Name of the user who submitted the report')
    organization_uuid: uuid.UUID = Field(default=uuid.UUID, foreign_key='organization.uuid', index=True)
    organization: 'Organization' = Relationship(back_populates='reports', sa_relationship_kwargs={'lazy': 'noload'})
    reported_at: Optional[datetime] = Field(default=None, nullable=True, description='Date and time of the report')
    project_uuid: uuid.UUID = Field(default=uuid.UUID, foreign_key='project.uuid', index=True)
    project: 'Project' = Relationship(back_populates='report', sa_relationship_kwargs={'lazy': 'noload'})
    comments: List['Comment'] = Relationship(back_populates='report', sa_relationship_kwargs={'lazy': 'noload'})
    status: ReportStatus = Field(default=ReportStatus.PENDING, description='Status of the report')
    activities: List['Activity'] = Relationship(back_populates='report', sa_relationship_kwargs={'lazy': 'noload'})
    reported_activities: List['ReportActivity'] = Relationship(back_populates='report', sa_relationship_kwargs={'lazy': 'noload'})
