from typing import Optional

import uuid
from pydantic import EmailStr
from sqlmodel import Field, Relationship, SQLModel
import sqlalchemy as sa

from db.models.address import BaseAddress
from db.models.base import CommonBaseModel


class OrganizationAddress(BaseAddress, table=True):
    __tablename__ = 'organization_address'

    country: Optional[str] = None
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
    home_country_address_id: Optional[uuid.UUID] = Field(default=None, foreign_key='organization_address.uuid')
    home_country_address: Optional[OrganizationAddress] = Relationship(back_populates='organizations', sa_relationship_kwargs={'lazy': 'selectin'})
    rwanda_address_id: uuid.UUID = Field(default=None, foreign_key='organization_address.uuid')
    rwanda_address: OrganizationAddress = Relationship(back_populates='organizations', sa_relationship_kwargs={'lazy': 'selectin'})
    organization_type_id: uuid.UUID = Field(default=uuid.UUID, foreign_key='organization_type.uuid')
    organization_type: 'OrganizationType' = Relationship(back_populates='organizations', sa_relationship_kwargs={'lazy': 'selectin'})
