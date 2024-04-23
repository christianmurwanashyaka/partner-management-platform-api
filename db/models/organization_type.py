from sqlmodel import Field

from db.models.base import CommonBaseModel


class OrganizationType(CommonBaseModel, table=True):
    __tablename__ = 'organization_type'

    name: str = Field(..., description="Name of the organization type")
    description: str | None = Field(default=None, nullable=True, description="Optional description of the organization type")
