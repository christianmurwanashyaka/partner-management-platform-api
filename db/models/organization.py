from __future__ import annotations
from typing import Optional, List

import uuid
from pydantic import EmailStr
from sqlmodel import Field, Relationship
import sqlalchemy as sa

from db.models import (
    OrganizationType,
    Project,
    Party,
    User,
    Report,
    FinancingScheme,
    HealthCareProvider,
    SubFinancingScheme,
    FinancingAgent,
    SubHealthCareProvider,
    SubFinancingAgent,
)
from db.models.base import CommonBaseModel
from db.models.document import Document


class OrganizationFinancingScheme(CommonBaseModel, table=True):
    __tablename__ = "organization_financing_scheme"

    organization_uuid: uuid.UUID = Field(
        default=None, foreign_key="organization.uuid", primary_key=True
    )
    financing_scheme_uuid: uuid.UUID = Field(
        default=None, foreign_key="financing_scheme.uuid", primary_key=True
    )


class OrganizationSubFinancingScheme(CommonBaseModel, table=True):
    __tablename__ = "organization_sub_financing_scheme"

    organization_uuid: uuid.UUID = Field(
        default=None, foreign_key="organization.uuid", primary_key=True
    )
    sub_financing_scheme_uuid: uuid.UUID = Field(
        default=None, foreign_key="sub_financing_scheme.uuid", primary_key=True
    )


class OrganizationHealthCareProvider(CommonBaseModel, table=True):
    __tablename__ = "organization_health_care_provider"

    organization_uuid: uuid.UUID = Field(
        default=None, foreign_key="organization.uuid", primary_key=True
    )
    health_care_provider_uuid: uuid.UUID = Field(
        default=None, foreign_key="health_care_provider.uuid", primary_key=True
    )


class OrganizationSubHealthCareProvider(CommonBaseModel, table=True):
    __tablename__ = "organization_sub_health_care_provider"

    organization_uuid: uuid.UUID = Field(
        default=None, foreign_key="organization.uuid", primary_key=True
    )
    sub_healthcare_provider_uuid: uuid.UUID = Field(
        default=None, foreign_key="sub_health_care_provider.uuid", primary_key=True
    )


class OrganizationFinancingAgent(CommonBaseModel, table=True):
    __tablename__ = "organization_financing_agent"

    organization_uuid: uuid.UUID = Field(
        default=None, foreign_key="organization.uuid", primary_key=True
    )
    financing_agent_uuid: uuid.UUID = Field(
        default=None, foreign_key="financing_agent.uuid", primary_key=True
    )


class OrganizationSubFinancingAgent(CommonBaseModel, table=True):
    __tablename__ = "organization_sub_financing_agent"

    organization_uuid: uuid.UUID = Field(
        default=None, foreign_key="organization.uuid", primary_key=True
    )
    sub_financing_agent_uuid: uuid.UUID = Field(
        default=None, foreign_key="sub_financing_agent.uuid", primary_key=True
    )


class Organization(CommonBaseModel, table=True):
    __tablename__ = "organization"

    name: str = Field(sa_column=sa.Column(sa.String, index=True))
    phone_number: str = Field(sa_column=sa.Column(sa.String))
    email: EmailStr = Field(sa_column=sa.Column(sa.String, unique=True))
    website: str = Field(sa_column=sa.Column(sa.String))

    home_country_representative: Optional[str] = Field(sa_column=sa.Column(sa.String))
    rwanda_representative: str = Field(sa_column=sa.Column(sa.String))

    # Home country address components
    home_country: Optional[str] = Field(sa_column=sa.Column(sa.String), default=None)
    home_country_province_state: Optional[str] = Field(
        sa_column=sa.Column(sa.String), default=None
    )
    home_country_district: Optional[str] = Field(
        sa_column=sa.Column(sa.String), default=None
    )
    home_country_avenue: Optional[str] = Field(
        sa_column=sa.Column(sa.String), default=None
    )
    home_country_po_box: Optional[str] = Field(
        sa_column=sa.Column(sa.String), default=None
    )

    # Rwanda address components
    rwanda_province: str = Field(sa_column=sa.Column(sa.String))
    rwanda_district: str = Field(sa_column=sa.Column(sa.String))
    rwanda_avenue: Optional[str] = Field(sa_column=sa.Column(sa.String), default=None)
    rwanda_po_box: Optional[str] = Field(sa_column=sa.Column(sa.String), default=None)

    rgb_number: Optional[str] = Field(sa_column=sa.Column(sa.String), default=None)

    organization_type_id: uuid.UUID = Field(
        default=None, sa_column=sa.Column(sa.ForeignKey("organization_type.uuid"))
    )
    organization_type: OrganizationType = Relationship(
        back_populates="organizations", sa_relationship_kwargs={"lazy": "noload"}
    )
    documents: List[Document] = Relationship(
        back_populates="organization", sa_relationship_kwargs={"lazy": "noload"}
    )

    projects: List[Project] = Relationship(
        back_populates="", sa_relationship_kwargs={"lazy": "noload"}
    )

    parties: List[Party] = Relationship(
        back_populates="", sa_relationship_kwargs={"lazy": "noload"}
    )

    users: List[User] = Relationship(
        back_populates="organization", sa_relationship_kwargs={"lazy": "noload"}
    )
    reports: List[Report] = Relationship(
        back_populates="organization", sa_relationship_kwargs={"lazy": "noload"}
    )

    financing_schemes: List[FinancingScheme] = Relationship(
        back_populates="organizations",
        link_model=OrganizationFinancingScheme,
        sa_relationship_kwargs={"lazy": "noload"},
    )

    health_care_providers: List[HealthCareProvider] = Relationship(
        back_populates="organizations",
        link_model=OrganizationHealthCareProvider,
        sa_relationship_kwargs={"lazy": "noload"},
    )

    financing_agents: List[FinancingAgent] = Relationship(
        back_populates="organizations",
        link_model=OrganizationFinancingAgent,
        sa_relationship_kwargs={"lazy": "noload"},
    )

    sub_financing_schemes: List[SubFinancingScheme] = Relationship(
        back_populates="organizations",
        link_model=OrganizationSubFinancingScheme,
        sa_relationship_kwargs={"lazy": "noload"},
    )

    sub_health_care_providers: List[SubHealthCareProvider] = Relationship(
        back_populates="organizations",
        link_model=OrganizationSubHealthCareProvider,
        sa_relationship_kwargs={"lazy": "noload"},
    )

    sub_financing_agents: List[SubFinancingAgent] = Relationship(
        back_populates="organizations",
        link_model=OrganizationSubFinancingAgent,
        sa_relationship_kwargs={"lazy": "noload"},
    )
