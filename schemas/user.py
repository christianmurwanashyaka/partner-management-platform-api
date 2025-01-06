import uuid
<<<<<<< HEAD

from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from uuid import UUID

=======
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

>>>>>>> 6af8bc40ba8f51251b6c9f5db9fe2a7ab8248eee
from db.models.user import UserRole, MOHStaffLevel


class UserBase(BaseModel):
    email: EmailStr
    first_name: str
    last_name: str
    role: UserRole


class UserCreate(UserBase):
    password: str
    phone_number: Optional[str] = None
    level: Optional[MOHStaffLevel] = None
    partner_organization_name: Optional[str] = None
    organization_uuid: Optional[uuid.UUID] = None


class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone_number: Optional[str] = None
    level: Optional[MOHStaffLevel] = None
    password: Optional[str] = None
    email: Optional[EmailStr] = None


class UserInDB(UserBase):
    id: int
    uuid: str

    class Config:
        from_attributes = True


class BaseToken(BaseModel):
    access_token: str
    token_type: str


class Token(BaseToken):
    first_name: str
    last_name: str
    role: str
    level: Optional[MOHStaffLevel] = None
    uuid: uuid.UUID


class TokenData(BaseModel):
    email: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserOrganization(BaseModel):
    uuid: UUID
    name: str
    email: EmailStr


class UserProfile(BaseModel):
    uuid: UUID
    first_name: str
    last_name: str
    email: EmailStr
    role: UserRole
    level: Optional[MOHStaffLevel] = None
    organizations: Optional[List[UserOrganization]] = None
    phone_number: Optional[str] = None

    class Config:
        from_attributes = True


class SignupResponse(BaseModel):
    user: UserProfile
<<<<<<< HEAD
    token: BaseToken
=======
    token: Optional[BaseToken] = None
>>>>>>> 6af8bc40ba8f51251b6c9f5db9fe2a7ab8248eee


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


class DomainAssignment(BaseModel):
    domain_uuid: uuid.UUID
    subdomain_uuids: Optional[List[uuid.UUID]] = None


class AssignDomains(BaseModel):
    user_uuid: uuid.UUID
    domain_assignments: List[DomainAssignment]


class OrganizationUserCreate(UserBase):
    pass

    class Config:
        from_attributes = True


class OrganizationUser(BaseModel):
    uuid: uuid.UUID
    email: EmailStr
    first_name: str
    last_name: str
    role: UserRole
    level: Optional[MOHStaffLevel] = None
    phone_number: Optional[str] = None
    organization_uuid: Optional[uuid.UUID] = None
    partner_organization_name: Optional[str] = None

    class Config:
        from_attributes = True


class PasswordResetRequest(BaseModel):
    new_password: str = Field(..., min_length=8)
