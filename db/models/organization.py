from typing import Optional, List

import uuid
from pydantic import EmailStr
from sqlmodel import Field, Relationship
import sqlalchemy as sa

from db.models.base import CommonBaseModel
from db.models.document import Document


class Organization(CommonBaseModel, table=True):
    __tablename__ = 'organization'

    name: str = Field(sa_column=sa.Column(sa.String, index=True))
    phone_number: str = Field(sa_column=sa.Column(sa.String))
    email: EmailStr = Field(sa_column=sa.Column(sa.String, unique=True))
    website: str = Field(sa_column=sa.Column(sa.String))

    home_country_representative: Optional[str] = Field(sa_column=sa.Column(sa.String))
    rwanda_representative: str = Field(sa_column=sa.Column(sa.String))

    # Home country address components
    home_country: Optional[str] = Field(sa_column=sa.Column(sa.String), default=None)
    home_country_province_state: Optional[str] = Field(sa_column=sa.Column(sa.String), default=None)
    home_country_district: Optional[str] = Field(sa_column=sa.Column(sa.String), default=None)
    home_country_avenue: Optional[str] = Field(sa_column=sa.Column(sa.String), default=None)
    home_country_po_box: Optional[str] = Field(sa_column=sa.Column(sa.String), default=None)

    # Rwanda address components
    rwanda_province: str = Field(sa_column=sa.Column(sa.String))
    rwanda_district: str = Field(sa_column=sa.Column(sa.String))
    rwanda_avenue: Optional[str] = Field(sa_column=sa.Column(sa.String), default=None)
    rwanda_po_box: Optional[str] = Field(sa_column=sa.Column(sa.String), default=None)

    rgb_number: Optional[str] = Field(sa_column=sa.Column(sa.String), default=None)

    organization_type_id: uuid.UUID = Field(
        default=None,
        sa_column=sa.Column(sa.ForeignKey('organization_type.uuid'))
    )
    organization_type: 'OrganizationType' = Relationship(
        back_populates='organizations',
        sa_relationship_kwargs={'lazy': 'selectin'}
    )
    documents: List[Document] = Relationship(
        back_populates='organization',
        sa_relationship_kwargs={'lazy': 'selectin'}
    )

    projects: List['Project'] = Relationship(back_populates='', sa_relationship_kwargs={'lazy': 'selectin'})

    parties: List['Party'] = Relationship(back_populates='', sa_relationship_kwargs={'lazy': 'selectin'})

    users: List['User'] = Relationship(back_populates='Organization', sa_relationship_kwargs={'lazy': 'selectin'})
