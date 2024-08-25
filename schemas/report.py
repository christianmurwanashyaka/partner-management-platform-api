import uuid
from datetime import date
from typing import Optional, List

from pydantic import BaseModel

from db.models import Currency
from db.models.activity import ActivityStatus, ActivityReportingStatus


class ActivityResponse(BaseModel):
    uuid: str
    name: str
    description: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    implementer: Optional[str] = None
    implementer_unit: Optional[str] = None
    fiscal_year: Optional[str] = None
    project_name: Optional[str] = None
    planned_budget: Optional[float] = None
    currency: Optional[Currency] = None
    status: Optional[ActivityStatus] = None
    report_status: Optional[ActivityReportingStatus] = None

    class Config:
        from_attributes = True


class PaginatedActivityResponse(BaseModel):
    items: List[ActivityResponse]
    total_items: int
    page: int
    page_size: int
    total_pages: int


class ActivityAssignment(BaseModel):
    user_uuid: uuid.UUID
    activity_uuid: List[uuid.UUID]


class ReportProjectActivityRead(BaseModel):
    uuid: uuid.UUID
    name: str

    class Config:
        from_attributes = True


class ProjectActivitiesResponse(BaseModel):
    project_name: str
    project_uuid: str
    activities: Optional[List[ActivityResponse]] = None


class PaginatedProjectActivitiesResponse(BaseModel):
    items: List[ProjectActivitiesResponse]
    total_items: int
    page: int
    page_size: int
    total_pages: int
