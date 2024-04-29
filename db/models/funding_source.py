from typing import List

from sqlmodel import Field, Relationship

from db.models.base import CommonBaseModel


class FundingSource(CommonBaseModel, table=True):
    __tablename__ = 'funding_source'
    name: str = Field(..., description="Name of the funding source")
    description: str | None = Field(default=None, nullable=True, description="Optional description of the funding source")
    projects: List['Project'] = Relationship(back_populates='funding_source', sa_relationship_kwargs={'lazy': 'selectin'})
