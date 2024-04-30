from pydantic import BaseModel, EmailStr
from typing import Optional, List
from uuid import UUID

from db.models.user import UserRole, SwapTeamLevel


class UserBase(BaseModel):
    email: EmailStr
    first_name: str
    last_name: str
    role: UserRole


class UserCreate(UserBase):
    password: str
    level: Optional[SwapTeamLevel] = None


class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    level: Optional[SwapTeamLevel] = None


class UserInDB(UserBase):
    id: int
    uuid: str

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str


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
    phone_number:int
    role: UserRole
    level: Optional[SwapTeamLevel] = None
    organizations: Optional[List[UserOrganization]] = None

    class Config:
        from_attributes = True


class SignupResponse(BaseModel):
    user: UserProfile
    token: Token
