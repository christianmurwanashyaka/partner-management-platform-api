from sqlmodel import Field

from db.models.base import CommonBaseModel


class FundingUnit(CommonBaseModel, table=True):
    __tablename__ = 'funding_unit'

    name: str = Field(..., description="Name of the funding unit")
    description: str | None = Field(default=None, nullable=True, description="Optional description of the funding unit")
