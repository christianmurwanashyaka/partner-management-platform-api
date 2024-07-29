from typing import List

from sqlmodel import Field, Relationship

from db.models.base import CommonBaseModel
from db.models.organization import Organization


class OrganizationType(CommonBaseModel, table=True):
    __tablename__ = 'organization_type'

    name: str = Field(..., description="Name of the organization type", index=True)
    description: str | None = Field(default=None, nullable=True, description="Optional description of the organization type")
    organizations: List[Organization] = Relationship(back_populates='organization_type')