from sqlmodel import Field

from db.models.base import CommonBaseModel


class FundingSource(CommonBaseModel, table=True):
    __tablename__ = 'funding_source'
    name: str = Field(..., description="Name of the funding source")
    description: str | None = Field(default=None, nullable=True, description="Optional description of the funding source")
