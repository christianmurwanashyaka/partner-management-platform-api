from passlib.context import CryptContext
from datetime import datetime, timedelta
from typing import Optional
from db.models.user import User
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import jwt
from dotenv import load_dotenv
from core.config import settings
from helpers.db import get_first_item

load_dotenv()


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRES_IN)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


async def create_admin(db: AsyncSession):
    admin_email = settings.EMAIL
    admin_password = get_password_hash(settings.PASSWORD)

    query = select(User).filter(User.email == admin_email)
    admin = await get_first_item(db, query)

    if not admin:
        admin = User(
            email=admin_email,
            password=admin_password,
            first_name=settings.FIRST_NAME,
            last_name=settings.LAST_NAME,
            role=settings.ROLE,
            created_by='system'
        )
        db.add(admin)
        await db.commit()
        await db.refresh(admin)

    return admin
