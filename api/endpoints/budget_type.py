import uuid
from datetime import datetime

from fastapi import APIRouter, Request, Depends, HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.future import select

from api.dependencies.access_control import admin_access, partner_access, moh_staff_access
from api.dependencies.auth import get_current_user
from db.database import get_db
from db.models import User
from db.models.budget_type import BudgetType
from db.models.pagination import PaginatedResponse
from schemas.budget_type import BudgetTypeRead, BudgetTypeCreate
from helpers.db import check_if_exists, get_all_items, get_first_item

router = APIRouter()


@router.post('/', response_model=BudgetTypeRead, dependencies=[Depends(admin_access)])
async def create_budget_type(request: Request, budget_type: BudgetTypeCreate, db: AsyncSession = Depends(get_db)):
    user = request.state.user.email

    if await check_if_exists(BudgetType, db, name=budget_type.name):
        raise HTTPException(status.HTTP_409_CONFLICT, detail='Budget type with this name already exists')

    new_budget_type = BudgetType(name=budget_type.name, description=budget_type.description, created_by=user)

    db.add(new_budget_type)
    await db.commit()
    await db.refresh(new_budget_type)
    return new_budget_type


@router.get('/', response_model=PaginatedResponse[BudgetTypeRead])
async def get_budget_types(page: int = 1, page_size: int = 100, db: AsyncSession = Depends(get_db)):
    return await get_all_items(db, BudgetType, page=page, page_size=page_size)


@router.get('/{uuid}', response_model=BudgetTypeRead)
async def get_budget_type(uuid: str, db: AsyncSession = Depends(get_db)):
    query = select(BudgetType).filter(BudgetType.uuid == uuid)
    budget_type = await get_first_item(db, query)
    if not budget_type:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail='Budget type not found')
    return budget_type


@router.delete('/{uuid}', response_model=BudgetTypeRead, dependencies=[Depends(admin_access)])
async def delete_budget_type(uuid: uuid.UUID, request: Request, db: AsyncSession = Depends(get_db)):
    user = request.state.user.email

    query = select(BudgetType).filter(BudgetType.uuid == uuid)
    budget_type = await get_first_item(db, query)
    if not budget_type:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail='Budget type not found')

    budget_type.deleted_status = True
    budget_type.deleted_by = user
    budget_type.last_updated_at = datetime.now()
    budget_type.last_updated_by = user

    await db.commit()
    await db.refresh(budget_type)
    return budget_type
