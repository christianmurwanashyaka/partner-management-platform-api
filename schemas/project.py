from datetime import datetime,date
from typing import List, Optional

import uuid
from pydantic import BaseModel

from schemas.budget_type import BudgetTypeRead
from schemas.domain_intervention import DomainInterventionRead


class OperationalZoneCreate(BaseModel):
    provinces: List[str]
    districts: List[str]

    class Config:
        from_attributes = True


class OperationalZoneRead(BaseModel):
    uuid: uuid.UUID
    provinces: List[str]
    districts: List[str]
    created_at: datetime
    created_by: str

    class Config:
        from_attributes = True


class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    domain_intervention_id: uuid.UUID
    budget_type_id: uuid.UUID
    planned_budget: float
    start_date: date
    end_date: date
    operational_zone: OperationalZoneCreate

    class Config:
        from_attributes = True


class ProjectList(BaseModel):
    uuid: uuid.UUID
    name: str
    description: Optional[str] = None
    planned_budget: float
    start_date: date
    end_date: date

    class Config:
        from_attributes = True


class ProjectRead(BaseModel):
    uuid: uuid.UUID
    name: str
    description: Optional[str] = None
    domain_intervention: DomainInterventionRead
    budget_type: BudgetTypeRead
    planned_budget: float
    start_date: date
    end_date: date
    operational_zone: OperationalZoneRead
    created_at: datetime
    created_by: str

    class Config:
        from_attributes = True
