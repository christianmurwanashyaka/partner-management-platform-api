from fastapi import APIRouter, Request, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies.auth import get_current_user
from db.database import get_db
from db.models import PaginatedResponse, User, Mou
from helpers.db import get_all_items
from schemas.mou import MouRead

router = APIRouter()


@router.get('/', response_model=PaginatedResponse[MouRead])
async def get_mous(
        page: int = 1,
        page_size: int = 100,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    try:
        if current_user.role not in ['admin', 'swapteam_member']:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail='You are not authorized to access this resource')

        mous = await get_all_items(db, Mou, page=page, page_size=page_size)

        return mous
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
