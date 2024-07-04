from typing import List

import uuid

from db.models import Currency
from db.models.base import CommonBaseModel
from sqlmodel import Field, Relationship


class Project(CommonBaseModel, table=True):
    __tablename__ = 'project'

    name: str = Field(..., description="Name of the project")
    description: str | None = Field(default=None, nullable=True, description="Optional description of the project")
    budget_type_id: uuid.UUID = Field(default=uuid.UUID, foreign_key='budget_type.uuid')
    budget_type: 'BudgetType' = Relationship(back_populates='projects', sa_relationship_kwargs={'lazy': 'selectin'})
    budget: float = Field(..., description="Planned budget of the project")
    currency: Currency = Field(default=Currency.RWF, description="Currency of the project's budget")
    organization_id: uuid.UUID = Field(default=uuid.UUID, foreign_key='organization.uuid')
    organization: 'Organization' = Relationship(back_populates='projects', sa_relationship_kwargs={'lazy': 'selectin'})
    funding_unit_id: uuid.UUID = Field(default=uuid.UUID, foreign_key='funding_unit.uuid')
    funding_unit: 'FundingUnit' = Relationship(back_populates='projects', sa_relationship_kwargs={'lazy': 'selectin'})
    funding_source_id: uuid.UUID = Field(default=uuid.UUID, foreign_key='funding_source.uuid')
    funding_source: 'FundingSource' = Relationship(back_populates='projects', sa_relationship_kwargs={'lazy': 'selectin'})
    activities: List['Activity'] = Relationship(back_populates='project', sa_relationship_kwargs={'lazy': 'selectin'})
    mou_details: List['MouDetail'] = Relationship(back_populates='project', sa_relationship_kwargs={'lazy': 'selectin'})
    overall_goal: str = Field(..., description="The overall goal of the project")
    goals: List['Goal'] = Relationship(back_populates='project', sa_relationship_kwargs={'lazy': 'selectin'})


class Goal(CommonBaseModel, table=True):
    __tablename__ = 'goal'

    name: str = Field(..., description="Name of the goal")
    description: str | None = Field(default=None, nullable=True, description="Optional description of the goal")
    project_id: uuid.UUID = Field(default=uuid.UUID, foreign_key='project.uuid')
    project: Project = Relationship(back_populates='goals', sa_relationship_kwargs={'lazy': 'selectin'})
