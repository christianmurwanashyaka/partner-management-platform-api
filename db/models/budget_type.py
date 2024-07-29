from typing import List

from db.models.base import CommonBaseModel
from sqlmodel import Field, Relationship


class BudgetType(CommonBaseModel, table=True):
    __tablename__ = 'budget_type'

    name: str = Field(..., description="Name of the budget type", index=True)
    description: str | None = Field(default=None, nullable=True, description="Optional description of the budget type")
    projects: List["Project"] = Relationship(back_populates='budget_type', sa_relationship_kwargs={'lazy': 'selectin'})
