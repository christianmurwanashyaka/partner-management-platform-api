from typing import List

from sqlmodel import Field, Relationship

from db.models.base import CommonBaseModel


class FundingUnit(CommonBaseModel, table=True):
    __tablename__ = 'funding_unit'

    name: str = Field(..., description="Name of the funding unit")
    description: str | None = Field(default=None, nullable=True, description="Optional description of the funding unit")
    projects: List['Project'] = Relationship(back_populates='funding_unit', sa_relationship_kwargs={'lazy': 'selectin'})
