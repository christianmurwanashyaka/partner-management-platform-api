import uuid
from typing import List, TYPE_CHECKING

from sqlmodel import Field, Relationship

from db.models import (
    CommonBaseModel,
    OrganizationSubFinancingScheme,
    OrganizationFinancingScheme,
)

if TYPE_CHECKING:
    from .types import Organization


class SubFinancingScheme(CommonBaseModel, table=True):
    __tablename__ = "sub_financing_scheme"

    financing_scheme_uuid: uuid.UUID = Field(
        default=uuid.UUID, foreign_key="financing_scheme.uuid"
    )
    financing_scheme: "FinancingScheme" = Relationship(
        back_populates="sub_financing_schemes",
        sa_relationship_kwargs={"lazy": "noload"},
    )
    name: str = Field(..., description="Name of the sub financing scheme", index=True)
    description: str | None = Field(
        default=None, description="Optional description for the sub financing scheme"
    )
    sha_code: str = Field(
        ...,
        description="SHA code for the sub financing scheme (e.g., FS.1.1",
        index=True,
    )
    organizations: List["Organization"] = Relationship(
        back_populates="sub_financing_schemes",
        link_model=OrganizationSubFinancingScheme,
        sa_relationship_kwargs={"lazy": "noload"},
    )


class FinancingScheme(CommonBaseModel, table=True):
    __tablename__ = "financing_scheme"

    name: str = Field(..., description="Name of the financing scheme", index=True)
    description: str | None = Field(
        default=None, description="Optional description for the financing scheme"
    )
    sha_code: str = Field(
        ..., description="SHA code for the financing scheme (e.g., FS.1", index=True
    )
    sub_financing_schemes: List[SubFinancingScheme] = Relationship(
        back_populates="financing_scheme", sa_relationship_kwargs={"lazy": "noload"}
    )
    organizations: List["Organization"] = Relationship(
        back_populates="financing_schemes",
        link_model=OrganizationFinancingScheme,
        sa_relationship_kwargs={"lazy": "noload"},
    )

    class Config:
        schema_extra = {
            "example": {
                "name": "Central government",
                "sha_code": "FA.1.1",
                "description": "Central government financing agent",
            }
        }
