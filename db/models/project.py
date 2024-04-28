import datetime
from typing import List

import uuid
from sqlalchemy import String, ARRAY, Column

from db.models.base import CommonBaseModel
from sqlmodel import Field, Relationship
import sqlalchemy as sa


class Project(CommonBaseModel, table=True):
    __tablename__ = 'project'

    name: str = Field(..., description="Name of the project")
    description: str | None = Field(default=None, nullable=True, description="Optional description of the project")
    domain_intervention_id: uuid.UUID = Field(default=uuid.UUID, foreign_key='domain_intervention.uuid')
    domain_intervention: 'DomainIntervention' = Relationship(back_populates='projects', sa_relationship_kwargs={'lazy': 'selectin'})
    budget_type_id: uuid.UUID = Field(default=uuid.UUID, foreign_key='budget_type.uuid')
    budget_type: 'BudgetType' = Relationship(back_populates='projects', sa_relationship_kwargs={'lazy': 'selectin'})
    planned_budget: float = Field(..., description="Planned budget of the project")
    start_date: datetime.date = Field(..., description="Start date of the project")
    end_date: datetime.date = Field(..., description="End date of the project")
    operational_zone: 'OperationalZone' = Relationship(back_populates='project', sa_relationship_kwargs={'lazy': 'selectin'})
    organization_id: uuid.UUID = Field(default=uuid.UUID, foreign_key='organization.uuid')
    organization: 'Organization' = Relationship(back_populates='projects', sa_relationship_kwargs={'lazy': 'selectin'})
    funding_unit_id: uuid.UUID = Field(default=uuid.UUID, foreign_key='funding_unit.uuid')
    funding_unit: 'FundingUnit' = Relationship(back_populates='projects', sa_relationship_kwargs={'lazy': 'selectin'})
    funding_source_id: uuid.UUID = Field(default=uuid.UUID, foreign_key='funding_source.uuid')
    funding_source: 'FundingSource' = Relationship(back_populates='projects', sa_relationship_kwargs={'lazy': 'selectin'})


class OperationalZone(CommonBaseModel, table=True):
    __tablename__ = 'operational_zone'

    project_id: uuid.UUID = Field(default=uuid.UUID, foreign_key='project.uuid')
    project: Project = Relationship(back_populates='operational_zone', sa_relationship_kwargs={'lazy': 'selectin'})
    provinces: List[str] = Field(sa_column=Column(ARRAY(String)), description="List of provinces in the operational zone")
    districts: List[str] = Field(sa_column=Column(ARRAY(String)), description="List of districts in the operational zone")
