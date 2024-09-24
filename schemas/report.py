import uuid
from datetime import date, datetime
from typing import Optional, List

from pydantic import BaseModel, UUID4

from db.models import Currency, ReportActivityStatus, Comment, ReportStatus
from db.models.activity import ActivityStatus, ActivityReportingStatus
from schemas.activity import ActivityDomainDetail
from schemas.input_detail import InputDetailRead


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
    input_details: Optional[List[InputDetailRead]] = None
    domains: Optional[List[ActivityDomainDetail]] = None

    class Config:
        from_attributes = True


class ActivityResponseDict(BaseModel):
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
    input_details: Optional[List[dict]] = None
    domains: Optional[List[dict]] = None


class ReportedActivityResponse(ActivityResponseDict):
    report_uuid: str
    reported_by: Optional[str] = None
    report_activity_uuid: str
    executed_budget: float
    actual_start_date: Optional[date] = None
    actual_end_date: Optional[date] = None
    report_activity_status: ReportActivityStatus
    accomplishments: Optional[List[str]] = None
    comments: List[Comment]

    class Config:
        from_attributes = True


class ReportedActivityProjectResponse(BaseModel):
    project_name: str
    project_uuid: str
    project_currency: Currency
    activities: Optional[List[ReportedActivityResponse]]


class PaginatedReportedActivityResponse(BaseModel):
    items: List[ReportedActivityProjectResponse]
    total_items: int
    page: int
    page_size: int
    total_pages: int


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
    project_currency: Currency
    activities: Optional[List[ActivityResponse]] = None


class PaginatedProjectActivitiesResponse(BaseModel):
    items: List[ProjectActivitiesResponse]
    total_items: int
    page: int
    page_size: int
    total_pages: int


class ReportResponse(BaseModel):
    uuid: UUID4
    mou_application_uuid: UUID4
    reported_by: Optional[str]
    organization_uuid: UUID4
    organization_name: str
    reported_at: Optional[datetime]
    project_uuid: UUID4
    project_name: str
    status: ReportStatus

    class Config:
        from_attributes = True


class PaginatedReportResponse(BaseModel):
    items: List[ReportResponse]
    total_items: int
    page: int
    page_size: int
    total_pages: int


class CommentResponse(BaseModel):
    uuid: uuid.UUID
    content: str
    created_at: datetime
    created_by: str

    class Config:
        from_attributes = True


class ReportActivityDetailResponse(BaseModel):
    uuid: uuid.UUID
    report_uuid: uuid.UUID
    reported_by: Optional[str]
    executed_budget: float
    actual_start_date: Optional[datetime]
    actual_end_date: Optional[datetime]
    status: ReportActivityStatus
    accomplishments: Optional[List[str]]
    comments: List[CommentResponse]
    report_status: ReportStatus
    project_name: str
    organization_name: str

    class Config:
        from_attributes = True
