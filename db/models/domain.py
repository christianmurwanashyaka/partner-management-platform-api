import uuid
from sqlmodel import Field, Relationship
from typing import List
from db.models.base import CommonBaseModel


class SubDomainFunction(CommonBaseModel, table=True):
    __tablename__ = 'sub_domain_function'

    name: str = Field(..., description="Name of the sub domain function")
    description: str | None = Field(default=None, nullable=True, description="Optional description of the sub domain function")
    sub_domain_id: uuid.UUID = Field(default=uuid.UUID, foreign_key='sub_domain.uuid')
    sub_domain: 'SubDomain' = Relationship(back_populates='functions', sa_relationship_kwargs={'lazy': 'selectin'})
    activities: List['ActivityDomain'] = Relationship(back_populates='sub_domain_function', sa_relationship_kwargs={'lazy': 'selectin'})


class SubDomain(CommonBaseModel, table=True):
    __tablename__ = 'sub_domain'

    name: str = Field(..., description="Name of the sub domain")
    description: str | None = Field(default=None, nullable=True, description="Optional description of the sub domain")
    domain_id: uuid.UUID = Field(default=uuid.UUID, foreign_key='domain_intervention.uuid')
    domain: 'DomainIntervention' = Relationship(back_populates='subdomains', sa_relationship_kwargs={'lazy': 'selectin'})
    functions: List[SubDomainFunction] = Relationship(back_populates='sub_domain', sa_relationship_kwargs={'lazy': 'selectin'})
    activities: List['ActivityDomain'] = Relationship(back_populates='sub_domain', sa_relationship_kwargs={'lazy': 'selectin'})


class DomainIntervention(CommonBaseModel, table=True):
    __tablename__ = 'domain_intervention'

    name: str = Field(..., description="Name of the domain intervention")
    description: str | None = Field(default=None, nullable=True, description="Optional description of the domain intervention")
    subdomains: List[SubDomain] = Relationship(back_populates='domain', sa_relationship_kwargs={'lazy': 'selectin'})

    activities: List['ActivityDomain'] = Relationship(back_populates='domain_intervention', sa_relationship_kwargs={'lazy': 'selectin'})
