from typing import Optional

import uuid
from pydantic import EmailStr
from sqlmodel import Field, Relationship, SQLModel
import sqlalchemy as sa
from db.models.base import CommonBaseModel


class Address(SQLModel):
    country: Optional[str] = None
    province_state: Optional[str] = None
    district: Optional[str] = None
    avenue: Optional[str] = None
    po_box: Optional[str] = None


class Organization(CommonBaseModel, table=True):
    __tablename__ = 'organization'

    name: str
    phone_number: str
    email: EmailStr = Field(sa_column=sa.Column(sa.String, unique=True, index=True))
    website: str
    home_country_representative: Optional[str] = None
    rwanda_representative: str
    home_country_address: Optional[Address] = None
    rwanda_address: Address
    organization_type_id: uuid.UUID = Field(default=uuid.UUID, foreign_key='organization_type.uuid')
    organization_type: 'OrganizationType' = Relationship(back_populates='organizations', sa_relationship_kwargs={'lazy': 'selectin'})
