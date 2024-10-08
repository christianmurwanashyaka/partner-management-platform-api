import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from db.models.activity import ActivityStatus
from schemas.report import ActivityResponse, ProjectActivitiesResponse


class ReportActivityCreate(BaseModel):
    activity_uuid: uuid.UUID
    executed_budget: float
    actual_start_date: datetime
    actual_end_date: datetime
    accomplishments: Optional[List[str]] = None
    comment: Optional[str] = None
    status: ActivityStatus

    class Config:
        from_attributes = True


class OrganizationProjectsResponse(BaseModel):
    organization_name: str
    organization_uuid: str
    projects: List[ProjectActivitiesResponse]


class PaginatedOrganizationProjectsResponse(BaseModel):
    items: List[OrganizationProjectsResponse]
    total_items: int
    page: int
    page_size: int
    total_pages: int


class RequestChange(BaseModel):
    comment: Optional[str] = None


class ReportActivityUpdateRequest(BaseModel):
    executed_budget: Optional[float] = None
    actual_start_date: Optional[datetime] = None
    actual_end_date: Optional[datetime] = None
    accomplishments: Optional[List[str]] = None
    comment: Optional[str] = None
    status: Optional[ActivityStatus] = None

    class Config:
        from_attributes = True

class ReportActivityUpdateResponse(BaseModel):
    executed_budget: float
    actual_start_date: datetime
    actual_end_date: datetime
    accomplishments: List[str]
    comment: Optional[str] = None
    status: ActivityStatus

    class Config:
        from_attributes = True