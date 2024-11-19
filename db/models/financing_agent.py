import uuid
from typing import List, TYPE_CHECKING

from sqlmodel import Field, Relationship

from db.models import CommonBaseModel

if TYPE_CHECKING:
    from .types import Organization


class SubFinancingAgent(CommonBaseModel, table=True):
    __tablename__ = "sub_financing_agent"

    financing_agent_uuid: uuid.UUID = Field(
        default=uuid.UUID, foreign_key="financing_agent.uuid", index=True
    )
    financing_agent: "FinancingAgent" = Relationship(
        back_populates="sub_financing_agents", sa_relationship_kwargs={"lazy": "noload"}
    )
    name: str = Field(..., description="Name of the sub financing agent", index=True)
    description: str | None = Field(
        default=None,
        nullable=True,
        description="Optional description of the sub financing agent",
    )
    sha_code: str = Field(
        ...,
        description="SHA code for the sub financing agent (e.g., FA.1.1)",
        index=True,
    )
    organizations: List["Organization"] = Relationship(
        back_populates="sub_financing_agents", sa_relationship_kwargs={"lazy": "noload"}
    )


class FinancingAgent(CommonBaseModel, table=True):
    __tablename__ = "financing_agent"

    name: str = Field(..., description="Name of the financing agent", index=True)
    description: str | None = Field(
        default=None,
        nullable=True,
        description="Optional description of the financing agent",
    )
    sha_code: str = Field(
        ..., description="SHA code for the financing agent (e.g., FA.1)", index=True
    )
    sub_financing_agents: List[SubFinancingAgent] = Relationship(
        back_populates="financing_agent", sa_relationship_kwargs={"lazy": "noload"}
    )
    organizations: List["Organization"] = Relationship(
        back_populates="financing_agents", sa_relationship_kwargs={"lazy": "noload"}
    )

    class Config:
        schema_extra = {
            "example": {
                "name": "Central government",
                "sha_code": "FA.1",
                "description": "Central government financing agent",
            }
        }
