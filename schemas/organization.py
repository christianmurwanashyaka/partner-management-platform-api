from typing import Optional

import uuid
from pydantic import BaseModel, EmailStr, field_validator

from schemas.address import OrganizationAddress
from schemas.organization_type import OrganizationTypeRead


class OrganizationCreate(BaseModel):
    name: str
    phone_number: str
    website: str
    email: EmailStr
    home_country_representative: Optional[str] = None
    rwanda_representative: str
    home_country_address: Optional[OrganizationAddress] = None
    rwanda_address: OrganizationAddress
    organization_type_id: uuid.UUID

    @field_validator('home_country_address', 'home_country_representative')
    def validate_home_country_fields(cls, v, field):
        if field.name == 'home_country_address' and cls.rwanda_address.country == 'Rwanda':
            return None
        if field.name == 'home_country_representative' and cls.rwanda_address.country == 'Rwanda':
            return None
        return v

    @field_validator('rwanda_address', 'rwanda_representative')
    def validate_rwanda_fields(cls, v, field):
        if not v:
            raise ValueError(f'{field.name.replace("_", " ").title()} is required.')
        return v


class OrganizationRead(BaseModel):
    uuid: uuid.UUID
    name: str
    phone_number: str
    email: EmailStr
    website: str
    home_country_representative: Optional[str] = None
    rwanda_representative: str
    home_country_address: Optional[OrganizationAddress] = None
    rwanda_address: OrganizationAddress
    organization_type: OrganizationTypeRead

    class Config:
        from_attributes = True
