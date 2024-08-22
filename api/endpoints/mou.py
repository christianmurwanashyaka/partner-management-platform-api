from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlmodel import select

from api.dependencies.auth import get_current_user
from db.database import get_db
from db.models import PaginatedResponse, User, Mou, MouApplication, MouDetail, Project
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
        if current_user.role not in ['admin', 'moh_staff']:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail='You are not authorized to access this resource')

        query = select(Mou).options(
            selectinload(Mou.mou_application).selectinload(MouApplication.mou_detail).selectinload(MouDetail.project).selectinload(Project.funding_unit),
            selectinload(Mou.mou_application).selectinload(MouApplication.mou_detail).selectinload(MouDetail.project).selectinload(Project.funding_source),
            selectinload(Mou.mou_application).selectinload(MouApplication.mou_detail).selectinload(MouDetail.project).selectinload(Project.budget_type)
        )

        # Calculate offset and limit based on page and page_size
        offset = (page - 1) * page_size
        limit = page_size

        # Apply offset and limit to the query
        query = query.offset(offset).limit(limit)

        mous = await db.execute(query)
        mous = mous.scalars().all()

        # Calculate total items count for pagination
        total_items_query = select(func.count(Mou.id))
        total_items = (await db.execute(total_items_query)).scalar_one()

        return PaginatedResponse(
            page=page,
            page_size=page_size,
            total_items=total_items,
            total_pages=(total_items + page_size - 1) // page_size,
            data=mous
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))