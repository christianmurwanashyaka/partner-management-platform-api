from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from db.database import get_db
from db.models.user import User
from helpers.db import get_first_item
from core.config import settings
import jwt

security = HTTPBearer()

credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="You are not logged in. Please log in to continue.",
    headers={"WWW-Authenticate": "Bearer"},
)

user_not_found_exception = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail="User not found",
)


async def get_current_user(
        request: Request,
        credentials: HTTPAuthorizationCredentials = Depends(security),
        db: AsyncSession = Depends(get_db)
) -> User:
    try:
        payload = jwt.decode(credentials.credentials, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception

    query = select(User).filter(User.email == user_id)
    user = await get_first_item(db, query)
    if not user:
        raise user_not_found_exception

    if user.deleted_status:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Your account has been suspended. Please contact the system admin.",
        )

    request.state.user = user
    return user

