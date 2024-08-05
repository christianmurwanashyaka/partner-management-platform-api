from datetime import date
from typing import Optional, List

from pydantic import BaseModel

from db.models import Currency


class ActivityResponse(BaseModel):
    uuid: str
    name: str
    description: Optional[str] = None
    start_date: date
    end_date: date
    implementer: str
    implementer_unit: str
    fiscal_year: str
    project_name: str
    planned_budget: float
    currency: Currency

    class Config:
        from_attributes = True


class PaginatedActivityResponse(BaseModel):
    items: List[ActivityResponse]
    total_items: int
    page: int
    page_size: int
    total_pages: int
