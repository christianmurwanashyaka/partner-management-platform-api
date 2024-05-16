from datetime import datetime,date
from typing import List, Optional

import uuid
from pydantic import BaseModel

from schemas.budget_type import BudgetTypeRead
from schemas.funding_source import FundingSourceRead
from schemas.funding_unit import FundingUnitRead


class GoalCreate(BaseModel):
    name: str
    description: Optional[str] = None

    class Config:
        from_attributes = True


class GoalRead(BaseModel):
    uuid: uuid.UUID
    name: str
    description: Optional[str] = None
    created_at: datetime
    created_by: str

    class Config:
        from_attributes = True


class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    budget_type_id: uuid.UUID
    budget: float
    currency: str
    organization_id: uuid.UUID
    funding_unit_id: uuid.UUID
    funding_source_id: uuid.UUID
    goals: List[GoalCreate]

    class Config:
        from_attributes = True


class ProjectList(BaseModel):
    uuid: uuid.UUID
    name: str
    description: Optional[str] = None
    budget: float
    currency: str
    start_date: date
    end_date: date

    class Config:
        from_attributes = True


class ProjectRead(BaseModel):
    uuid: uuid.UUID
    name: str
    description: Optional[str] = None
    budget_type: BudgetTypeRead
    funding_unit: FundingUnitRead
    funding_source: FundingSourceRead
    budget: float
    currency: str
    created_at: datetime
    created_by: str
    goals: List[GoalRead]

    class Config:
        from_attributes = True
