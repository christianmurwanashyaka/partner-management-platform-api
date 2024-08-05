import uuid
from typing import List

from sqlmodel import Field, Relationship
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY

from db.models import CommonBaseModel


class UserDomain(CommonBaseModel, table=True):
    __tablename__ = 'user_domain'

    user_id: uuid.UUID = Field(default=uuid.UUID, foreign_key='user.uuid', index=True)
    user: 'User' = Relationship(back_populates='domains', sa_relationship_kwargs={'lazy': 'selectin'})

    domain_id: uuid.UUID = Field(default=uuid.UUID, foreign_key='domain_intervention.uuid', index=True)
    domain_intervention: 'DomainIntervention' = Relationship(back_populates='users', sa_relationship_kwargs={'lazy': 'selectin'})

    subdomain_ids: List[uuid.UUID] = Field(sa_column=sa.Column(ARRAY(sa.UUID)))
    subdomains: List['SubDomain'] = Relationship(
        back_populates='user_domains',
        sa_relationship_kwargs={
            'primaryjoin': 'SubDomain.uuid == any_(foreign(UserDomain.subdomain_ids))',
            'lazy': 'selectin'
        }
    )
