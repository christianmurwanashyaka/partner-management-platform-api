from typing import List, Optional

import uuid

from pydantic import field_validator
from sqlalchemy import String, ARRAY, Column, Float, JSON

from db.models import Currency
from db.models.base import CommonBaseModel
from sqlmodel import Field, Relationship


class Project(CommonBaseModel, table=True):
    __tablename__ = 'project'

    name: str = Field(..., description="Name of the project")
    description: str | None = Field(default=None, nullable=True, description="Optional description of the project")
    budget_type_id: uuid.UUID = Field(default=uuid.UUID, foreign_key='budget_type.uuid')
    budget_type: 'BudgetType' = Relationship(back_populates='projects', sa_relationship_kwargs={'lazy': 'selectin'})
    fiscal_year_budgets: List[dict] = Field(
        sa_column=Column(JSON),
        description="List of dictionaries containing fiscal year and budget for each year of the project"
    )
    currency: Currency = Field(default=Currency.RWF, description="Currency of the project's budget")
    total_budget: float = Field(default=0.0, description="Total budget of the project")
    organization_id: uuid.UUID = Field(default=uuid.UUID, foreign_key='organization.uuid')
    organization: 'Organization' = Relationship(back_populates='projects', sa_relationship_kwargs={'lazy': 'selectin'})
    funding_unit_id: uuid.UUID = Field(default=uuid.UUID, foreign_key='funding_unit.uuid')
    funding_unit: 'FundingUnit' = Relationship(back_populates='projects', sa_relationship_kwargs={'lazy': 'selectin'})
    funding_source_id: Optional[uuid.UUID] = Field(default=None, foreign_key='funding_source.uuid')
    funding_source: Optional['FundingSource'] = Relationship(back_populates='projects', sa_relationship_kwargs={'lazy': 'selectin'})
    other_funding_source: Optional[str] = Field(
        default=None, nullable=True, description="Name of the funding source if not in the predefined list")
    activities: List['Activity'] = Relationship(back_populates='project', sa_relationship_kwargs={'lazy': 'selectin'})
    mou_details: List['MouDetail'] = Relationship(back_populates='project', sa_relationship_kwargs={'lazy': 'selectin'})
    overall_goal: str = Field(..., description="The overall goal of the project")
    goals: List['Goal'] = Relationship(back_populates='project', sa_relationship_kwargs={'lazy': 'selectin'})
    duration: str | None = Field(default=None, nullable=True, description="The duration of the project")

    @field_validator('fiscal_year_budgets')
    def check_fiscal_year_budgets(cls, v):
        if not v:
            raise ValueError("At least one fiscal year budget must be provided")
        fiscal_years = set()
        for item in v:
            if 'fiscal_year' not in item or 'budget' not in item:
                raise ValueError("Each fiscal year budget must have 'fiscal_year' and 'budget' keys")
            if item['fiscal_year'] in fiscal_years:
                raise ValueError(f"Duplicate fiscal year: {item['fiscal_year']}")
            fiscal_years.add(item['fiscal_year'])
        return v


class Goal(CommonBaseModel, table=True):
    __tablename__ = 'goal'

    name: str = Field(..., description="Name of the goal")
    description: str | None = Field(default=None, nullable=True, description="Optional description of the goal")
    project_id: uuid.UUID = Field(default=uuid.UUID, foreign_key='project.uuid')
    project: Project = Relationship(back_populates='goals', sa_relationship_kwargs={'lazy': 'selectin'})
