import uuid
from fastapi import APIRouter, Request, Depends, HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.future import select

from api.dependencies.access_control import admin_access
from api.dependencies.auth import get_current_user
from db.database import get_db
from db.models.user import User, UserRole
from db.models.pagination import PaginatedResponse
from schemas.user import UserProfile, UserCreate, SignupResponse, UserUpdate
from helpers.db import check_if_exists, get_all_items, get_first_item
from utils.security import get_password_hash

router = APIRouter()


@router.get('/', response_model=PaginatedResponse[UserProfile], dependencies=[Depends(admin_access)])
async def get_users(page: int = 1, page_size: int = 100, db: AsyncSession = Depends(get_db)):
    return await get_all_items(db, User, page=page, page_size=page_size)


@router.patch('/{uuid}', response_model=UserProfile)
async def update_user(
        uuid: uuid.UUID,
        user_update: UserUpdate,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    try:
        query = select(User).where(User.uuid == uuid)
        result = await db.execute(query)
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail='User not found')

        if user.email != current_user.email and current_user.role != UserRole.ADMIN:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail='Not authorized to update this user')

        update_data = user_update.dict(exclude_unset=True)

        if 'password' in update_data:
            update_data['password'] = get_password_hash(update_data['password'])

        for key, value in update_data.items():
            setattr(user, key, value)

        await db.commit()
        await db.refresh(user)

        return user
    except Exception as e:
        await db.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
