from __future__ import annotations
import uuid
from typing import List

from sqlmodel import Field, Relationship

from db.models import CommonBaseModel, Organization


class SubHealthCareProvider(CommonBaseModel, table=True):
    __tablename__ = "sub_health_care_provider"

    health_care_provider_uuid: uuid.UUID = Field(
        default=uuid.UUID, foreign_key="health_care_provider.uuid"
    )
    health_care_provider: "HealthCareProvider" = Relationship(
        back_populates="sub_health_care_providers",
        sa_relationship_kwargs={"lazy": "noload"},
    )
    name: str = Field(
        ..., description="Name of the sub health care provider", index=True
    )
    description: str | None = Field(
        default=None, description="Description of the sub health care provider"
    )
    sha_code: str = Field(
        ...,
        description="SHA code of the sub health care provider (e.g., HP1.1",
        index=True,
    )
    organizations: List[Organization] = Relationship(
        back_populates="sub_health_care_providers",
        sa_relationship_kwargs={"lazy": "noload"},
    )


class HealthCareProvider(CommonBaseModel, table=True):
    __tablename__ = "health_care_provider"

    sub_health_care_providers: List["SubHealthCareProvider"] = Relationship(
        back_populates="health_care_provider", sa_relationship_kwargs={"lazy": "noload"}
    )
    name: str = Field(..., description="Name of the health care provider", index=True)
    description: str | None = Field(
        default=None, description="Description of the health care provider"
    )
    sha_code: str = Field(
        ..., description="SHA code of the health care provider", index=True
    )
    organizations: List[Organization] = Relationship(
        back_populates="health_care_providers",
        sa_relationship_kwargs={"lazy": "noload"},
    )

    class Config:
        schema_extra = {
            "example": {
                "name": "Central government",
                "sha_code": "HP.1",
                "description": "Central government financing agent",
            }
        }
