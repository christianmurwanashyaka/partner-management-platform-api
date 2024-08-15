import uuid
from datetime import datetime
from enum import Enum
from typing import List, Optional

from sqlalchemy import Column, ARRAY, String
from sqlmodel import Field, Relationship

from db.models import CommonBaseModel


class ReportActivityStatus(str, Enum):
    PENDING = 'pending'
    APPROVED = 'approved'
    NEEDS_CHANGE = 'needs_change'


class ReportActivity(CommonBaseModel, table=True):
    __tablename__ = 'report_activity'

    report_uuid: uuid.UUID = Field(default=uuid.UUID, foreign_key='report.uuid', index=True)
    report: 'Report' = Relationship(back_populates='reported_activities', sa_relationship_kwargs={'lazy': 'selectin'})
    reported_by: Optional[str] = Field(default=None, nullable=True, description='Name of the user who reported the MOU application')
    executed_budget: float = Field(default=0.0, description="The executed budget for the activity")
    actual_start_date: datetime = Field(default=None, nullable=True, description="The actual start date of the activity")
    actual_end_date: datetime = Field(default=None, nullable=True, description="The actual end date of the activity")
    comments: List['Comment'] = Relationship(back_populates='report_activity', sa_relationship_kwargs={'lazy': 'selectin'})
    status: ReportActivityStatus = Field(default=ReportActivityStatus.PENDING, index=True)
    accomplishments: Optional[List[str]] = Field(sa_column=Column(ARRAY(String)), description="List of accomplishments of the activity")
