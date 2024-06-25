import uuid
from sqlmodel import Field, Relationship
from db.models.base import CommonBaseModel


class ActivityDomain(CommonBaseModel, table=True):
    __tablename__ = 'activity_domain'

    activity_id: uuid.UUID = Field(default=uuid.UUID, foreign_key='activity.uuid')
    activity: 'Activity' = Relationship(back_populates='domains', sa_relationship_kwargs={'lazy': 'selectin'})

    domain_intervention_id: uuid.UUID = Field(default=uuid.UUID, foreign_key='domain_intervention.uuid')
    domain_intervention: 'DomainIntervention' = Relationship(back_populates='activities', sa_relationship_kwargs={'lazy': 'selectin'})

    sub_domain_id: uuid.UUID = Field(default=uuid.UUID, foreign_key='sub_domain.uuid')
    sub_domain: 'SubDomain' = Relationship(back_populates='activities', sa_relationship_kwargs={'lazy': 'selectin'})

    sub_domain_function_id: uuid.UUID = Field(default=uuid.UUID, foreign_key='sub_domain_function.uuid')
    sub_domain_function: 'SubDomainFunction' = Relationship(back_populates='activities', sa_relationship_kwargs={'lazy': 'selectin'})

    sub_function_id: uuid.UUID = Field(default=uuid.UUID, foreign_key='sub_function.uuid')
    sub_function: 'SubFunction' = Relationship(back_populates='activities', sa_relationship_kwargs={'lazy': 'selectin'})
