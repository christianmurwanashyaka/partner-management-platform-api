from db.models.base import CommonBaseModel
from sqlmodel import Field


class BudgetType(CommonBaseModel, table=True):
    __tablename__ = 'budget_type'

    name: str = Field(..., description="Name of the budget type")
    description: str | None = Field(default=None, nullable=True, description="Optional description of the budget type")
