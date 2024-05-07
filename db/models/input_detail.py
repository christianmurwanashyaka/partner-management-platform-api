from typing import List

import uuid
from sqlalchemy import Column, ARRAY, String
from sqlmodel import Field, Relationship

from db.models.base import CommonBaseModel


class InputDetail(CommonBaseModel, table=True):
    __tablename__ = 'input_detail'

    activity_id: uuid.UUID = Field(default=uuid.UUID, foreign_key='activity.uuid')
    activity: 'Activity' = Relationship(back_populates='input_details', sa_relationship_kwargs={'lazy': 'selectin'})

    input_category_id: uuid.UUID = Field(default=uuid.UUID, foreign_key='input_category.uuid')
    input_category: 'InputCategory' = Relationship(back_populates='input_details', sa_relationship_kwargs={'lazy': 'selectin'})

    input_id: uuid.UUID = Field(default=uuid.UUID, foreign_key='input.uuid')
    input: 'Input' = Relationship(back_populates='input_details', sa_relationship_kwargs={'lazy': 'selectin'})

    budget: float = Field(..., description='Budget for the selected input')
    districts: List[str] = Field(sa_column=Column(ARRAY(String)), description='List of districts for the input detail')
    provinces: List[str] = Field(sa_column=Column(ARRAY(String)), description='List of provinces for the input detail')
