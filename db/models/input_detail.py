import uuid
from sqlmodel import Field, Relationship

from db.models.base import CommonBaseModel


class InputDetail(CommonBaseModel, table=True):
    __tablename__ = 'input_detail'

    activity_id: uuid.UUID = Field(default=uuid.UUID, foreign_key='activity.uuid')
    activity: 'Activity' = Relationship(back_populates='input_details', sa_relationship_kwargs={'lazy': 'selectin'})

    input_category_id: uuid.UUID = Field(default=uuid.UUID, foreign_key='input_category.uuid')
    input_category: 'InputCategory' = Relationship(sa_relationship_kwargs={'lazy': 'selectin'})

    input_id: uuid.UUID = Field(default=uuid.UUID, foreign_key='input.uuid')
    input: 'Input' = Relationship(sa_relationship_kwargs={'lazy': 'selectin'})

    budget: float = Field(..., description='Budget for the selected input')
