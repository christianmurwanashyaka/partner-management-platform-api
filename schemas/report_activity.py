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
