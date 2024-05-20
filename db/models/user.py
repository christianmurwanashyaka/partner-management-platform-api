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


class MOHStaffLevel(str, Enum):
    PARTNER_COORDINATOR = "partner_coordinator"
    TECHNICAL_DEPARTMENT = "technical_department"
    LEGAL_ADVISOR = "legal_advisor"
    HOD = "hod"
    PS = "ps"
    MINISTER_OF_STATE = "minister_of_state"
    MINISTER = "minister"


class User(CommonBaseModel, table=True):
    __tablename__ = 'user'
    email: EmailStr = Field(sa_column=sa.Column(sa.String, unique=True, index=True))
    password: str
    first_name: str
    last_name: str
    role: UserRole
    level: Optional[MOHStaffLevel] = None
    phone_number: Optional[str] = None
    notifications: Optional[List['Notification']] = Relationship(back_populates='recipient', sa_relationship_kwargs={'lazy': 'selectin'})
