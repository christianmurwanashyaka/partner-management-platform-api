from fastapi import APIRouter, Request, Depends, HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.future import select

from api.dependencies.access_control import admin_access
from db.database import get_db
from db.models.user import User
from db.models.pagination import PaginatedResponse
from schemas.user import UserProfile
from helpers.db import check_if_exists, get_all_items, get_first_item

router = APIRouter()


@router.get('/', response_model=PaginatedResponse[UserProfile], dependencies=[Depends(admin_access)])
async def get_users(page: int = 1, page_size: int = 100, db: AsyncSession = Depends(get_db)):
    return await get_all_items(db, User, page=page, page_size=page_size)
