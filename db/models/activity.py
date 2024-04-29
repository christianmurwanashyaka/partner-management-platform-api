from typing import List

import uuid
from sqlalchemy import String, ARRAY, Column
from sqlmodel import Field, Relationship

from db.models.base import CommonBaseModel


class Activity(CommonBaseModel, table=True):
    __tablename__ = 'activity'

    project_id: uuid.UUID = Field(default=uuid.UUID, foreign_key='project.uuid')
    project: 'Project' = Relationship(back_populates='activities', sa_relationship_kwargs={'lazy': 'selectin'})

    name: str = Field(..., description='Name of the activity')
    implementer: str = Field(..., description='Name of the implementer of the activity')
    fiscal_year: str = Field(..., description='Fiscal year of the activity')

    sub_domain_id: uuid.UUID = Field(default=uuid.UUID, foreign_key='sub_domain.uuid')
    sub_domain: 'SubDomain' = Relationship(sa_relationship_kwargs={'lazy': 'selectin'})

    districts: List[str] = Field(sa_column=Column(ARRAY(String)), description='List of districts for the activity')
    provinces: List[str] = Field(sa_column=Column(ARRAY(String)), description='List of provinces for the activity')

    input_details: List['InputDetail'] = Relationship(back_populates='activity', sa_relationship_kwargs={'lazy': 'selectin'})
