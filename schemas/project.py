from datetime import datetime,date
from typing import List, Optional, Union

import uuid
from pydantic import BaseModel

from db.models import Currency
from schemas.activity import ActivityList
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
    funding_source_id: Optional[uuid.UUID] = None
    other_funding_source: Optional[str] = None
    overall_goal: str
    goals: List[GoalCreate]
    duration: Optional[str] = None

    class Config:
        from_attributes = True


class ProjectList(BaseModel):
    uuid: uuid.UUID
    name: str
    description: Optional[str] = None
    budget: float
    currency: Currency
    duration: Optional[str] = None

    class Config:
        from_attributes = True


class ProjectRead(BaseModel):
    uuid: uuid.UUID
    name: str
    description: Optional[str] = None
    budget_type: BudgetTypeRead
    funding_unit: FundingUnitRead
    funding_source: Optional[FundingSourceRead] = None
    other_funding_source: Optional[str] = None
    budget: float
    currency: str
    created_at: datetime
    created_by: str
    overall_goal: str
    goals: List[GoalRead]
    activities: List[ActivityList] = []
    duration: Optional[str] = None

    class Config:
        from_attributes = True


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    budget_type_id: Optional[uuid.UUID] = None
    budget: Optional[float] = None
    currency: Optional[str] = None
    funding_unit_id: Optional[uuid.UUID] = None
    funding_source_id: Optional[uuid.UUID] = None
    overall_goal: Optional[str] = None
    goals: Optional[List[GoalCreate]] = None
    duration: Optional[str] = None

    class Config:
        from_attributes = True
