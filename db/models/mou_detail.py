from typing import List, Optional

import uuid
from sqlmodel import Field, Relationship

from db.models import CommonBaseModel, Document


class MouDetail(CommonBaseModel, table=True):
    __tablename__ = 'mou_detail'

    project_id: uuid.UUID = Field(default=uuid.UUID, foreign_key='project.uuid')
    project: 'Project' = Relationship(back_populates='mou_details', sa_relationship_kwargs={'lazy': 'selectin'})
    parties: List['Party'] = Relationship(back_populates='mou_detail', sa_relationship_kwargs={'lazy': 'selectin'})
    mou_application: Optional['MouApplication'] = Relationship(back_populates='mou_detail', sa_relationship_kwargs={'lazy': 'selectin'})
    documents: List[Document] = Relationship(back_populates='mou_detail', sa_relationship_kwargs={'lazy': 'selectin'})
