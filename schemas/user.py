from pydantic import BaseModel, EmailStr
from typing import Optional, List
from uuid import UUID

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
    token: BaseToken


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str
