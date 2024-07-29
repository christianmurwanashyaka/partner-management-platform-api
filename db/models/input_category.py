from typing import List
from sqlmodel import Relationship, Field
from db.models.base import CommonBaseModel
import uuid


class Input(CommonBaseModel, table=True):
    __tablename__ = 'input'

    category_id: uuid.UUID = Field(default=uuid.UUID, foreign_key='input_category.uuid', index=True)
    category: 'InputCategory' = Relationship(back_populates='inputs', sa_relationship_kwargs={'lazy': 'selectin'})
    name: str = Field(..., description='Name of the input')
    description: str | None = Field(default=None, nullable=True, description='Optional description of the input')
    input_details: List['InputDetail'] = Relationship(back_populates='input', sa_relationship_kwargs={'lazy': 'selectin'})


class InputCategory(CommonBaseModel, table=True):
    __tablename__ = 'input_category'

    name: str = Field(..., description="Name of the input category", index=True)
    description: str | None = Field(default=None, nullable=True, description="Optional description of the input category")
    inputs: List[Input] = Relationship(back_populates='category', sa_relationship_kwargs={'lazy': 'selectin'})
    input_details: List['InputDetail'] = Relationship(back_populates='input_category', sa_relationship_kwargs={'lazy': 'selectin'})
