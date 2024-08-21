import uuid
from enum import Enum
from typing import Optional, List

from pydantic import EmailStr
from sqlmodel import Field, Relationship
import sqlalchemy as sa

from db.models.base import CommonBaseModel


class UserRole(str, Enum):
    PARTNER = "partner"
    ADMIN = "admin"
    MOH_STAFF = "moh_staff"
    DATA_MANAGER = "data_manager"
    DATA_REPORTER = "data_reporter"


class MOHStaffLevel(str, Enum):
    PARTNER_COORDINATOR = "partner_coordinator"
    TECHNICAL_DEPARTMENT = "technical_department"
    LEGAL_ADVISOR = "legal_advisor"
    HOD = "hod"
    PS = "ps"
    MINISTER = "minister"


class User(CommonBaseModel, table=True):
    __tablename__ = 'user'
    email: EmailStr = Field(sa_column=sa.Column(sa.String, unique=True, index=True))
    password: str
    first_name: str
    last_name: str
    role: UserRole
    level: Optional[MOHStaffLevel] = None
    phone_number    : Optional[str] = None
    organization_uuid: Optional[uuid.UUID] = Field(default=None, foreign_key='organization.uuid')
    organization: Optional['Organization'] = Relationship(
        back_populates="users", sa_relationship_kwargs={'lazy': 'noload'})
    notifications: Optional[List['Notification']] = Relationship(
        back_populates='recipient', sa_relationship_kwargs={'lazy': 'noload'})
    domains: List['UserDomain'] = Relationship(back_populates='user', sa_relationship_kwargs={'lazy': 'noload'})
    partner_organization_name: Optional[str] = None
    activities: List['UserActivity'] = Relationship(back_populates='user', sa_relationship_kwargs={'lazy': 'noload'})
