from datetime import datetime,date
from typing import List, Optional, Union

import uuid
from pydantic import BaseModel, field_validator
from pydantic_core.core_schema import ValidationInfo

from db.models import Currency
from schemas.activity import ActivityList
from schemas.budget_type import BudgetTypeRead
from schemas.funding_source import FundingSourceRead
from schemas.funding_unit import FundingUnitRead
from schemas.report import ReportProjectActivityRead


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


class FiscalYearBudget(BaseModel):
    fiscal_year: str
    budget: float


class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    budget_type_id: uuid.UUID
    fiscal_year_budgets: List[FiscalYearBudget]
    total_budget: Optional[float] = None
    currency: str
    organization_id: uuid.UUID
    funding_unit_id: uuid.UUID
    funding_source_id: Optional[uuid.UUID] = None
    other_funding_source: Optional[str] = None
    overall_goal: str
    goals: List[GoalCreate]
    duration: Optional[str] = None

    @field_validator('fiscal_year_budgets')
    def check_fiscal_year_budgets(cls, v):
        if not v:
            raise ValueError("At least one fiscal year budget must be provided")
        fiscal_years = set()
        for item in v:
            if item.fiscal_year in fiscal_years:
                raise ValueError(f"Duplicate fiscal year: {item.fiscal_year}")
            fiscal_years.add(item.fiscal_year)
        return v

    @field_validator('total_budget')
    def check_total_budget(cls, v: Optional[float], info: ValidationInfo) -> Optional[float]:
        fiscal_year_budgets = info.data.get('fiscal_year_budgets', [])
        if v is not None and fiscal_year_budgets:
            calculated_total = sum(item.budget for item in fiscal_year_budgets)
            if abs(v - calculated_total) > 0.01:
                raise ValueError("Provided total budget does not match the sum of fiscal year budgets")
        return v

    class Config:
        from_attributes = True


class ProjectList(BaseModel):
    uuid: uuid.UUID
    name: str
    description: Optional[str] = None
    fiscal_year_budgets: List[FiscalYearBudget]
    currency: Currency
    duration: Optional[str] = None
    total_budget: float
    activities: Optional[List[ActivityList]] = None

    class Config:
        from_attributes = True


class ProjectRead(BaseModel):
    uuid: uuid.UUID
    name: str
    description: Optional[str] = None
    budget_type: Optional[BudgetTypeRead] = None
    funding_unit: Optional[FundingUnitRead] = None
    funding_source: Optional[FundingSourceRead] = None
    other_funding_source: Optional[str] = None
    fiscal_year_budgets: Optional[List[FiscalYearBudget]] = None
    total_budget: Optional[float] = None
    currency: Optional[str] = None
    created_at: Optional[datetime] = None
    created_by: Optional[str] = None
    overall_goal: Optional[str] = None
    goals: Optional[List[GoalRead]] = None
    activities: Optional[List[ActivityList]] = None
    duration: Optional[str] = None

    class Config:
        from_attributes = True


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    budget_type_id: Optional[uuid.UUID] = None
    fiscal_year_budgets: Optional[List[FiscalYearBudget]] = None
    total_budget: Optional[float] = None
    currency: Optional[str] = None
    funding_unit_id: Optional[uuid.UUID] = None
    funding_source_id: Optional[uuid.UUID] = None
    overall_goal: Optional[str] = None
    goals: Optional[List[GoalCreate]] = None
    duration: Optional[str] = None

    @field_validator('total_budget')
    def check_total_budget(cls, v: Optional[float], info: ValidationInfo) -> Optional[float]:
        fiscal_year_budgets = info.data.get('fiscal_year_budgets')
        if v is not None and fiscal_year_budgets is not None:
            calculated_total = sum(item.budget for item in fiscal_year_budgets)
            if abs(v - calculated_total) > 0.01:
                raise ValueError("Provided total budget does not match the sum of fiscal year budgets")
        return v

    class Config:
        from_attributes = True
