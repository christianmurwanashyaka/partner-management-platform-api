import uuid
from sqlmodel import Field, Relationship

from db.models import CommonBaseModel


class OperationalZone(CommonBaseModel, table=True):
    __tablename__ = 'operational_zone'

    activity_id: uuid.UUID = Field(default=uuid.UUID, foreign_key='activity.uuid')
    activity: 'Activity' = Relationship(back_populates='operational_zones', sa_relationship_kwargs={'lazy': 'noload'})
    province: str = Field(..., description="Province in the operational zone")
    district: str = Field(..., description="District in the operational zone")
