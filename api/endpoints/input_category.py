import uuid
from datetime import datetime

from fastapi import APIRouter, Request, Depends, HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.future import select

from api.dependencies.access_control import admin_access, partner_access, moh_staff_access
from api.dependencies.auth import get_current_user
from db.database import get_db
from db.models import User
from db.models.input_category import InputCategory, Input
from db.models.pagination import PaginatedResponse
from schemas.input_category import InputCategoryList, InputCategoryRead, InputCategoryCreate
from helpers.db import check_if_exists, get_all_items, get_first_item, get_joined_details_by_uuid

router = APIRouter()


@router.post('/', response_model=InputCategoryRead, dependencies=[Depends(admin_access)])
async def create_input_category(request: Request, input_category: InputCategoryCreate, db: AsyncSession = Depends(get_db)):
    user = request.state.user.email

    if await check_if_exists(InputCategory, db, name=input_category.name):
        raise HTTPException(status.HTTP_409_CONFLICT, detail='Input category with this name already exists')

    new_input_category = InputCategory(name=input_category.name, description=input_category.description, created_by=user)

    db.add(new_input_category)
    try:
        await db.commit()
        await db.refresh(new_input_category)
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    return new_input_category


@router.get('/', response_model=PaginatedResponse[InputCategoryList])
async def get_input_categories(page: int = 1, page_size: int = 100, db: AsyncSession = Depends(get_db)):
    return await get_all_items(db, InputCategory, page=page, page_size=page_size)


@router.get('/{uuid}', response_model=InputCategoryRead)
async def get_input_category(uuid: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    input_category = await get_joined_details_by_uuid(
        db=db,
        model=InputCategory,
        alias_model=Input,
        join_condition=lambda alias: alias.category_id == InputCategory.uuid, uuid=uuid,
        relationship_option=InputCategory.inputs)
    if not input_category:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail='Input category not found')
    return input_category


@router.delete('/{uuid}', response_model=InputCategoryRead, dependencies=[Depends(admin_access)])
async def delete_input_category(uuid: uuid.UUID, request: Request, db: AsyncSession = Depends(get_db)):
    user = request.state.user.email
    query = select(InputCategory).filter(InputCategory.uuid == uuid)
    input_category = await get_first_item(db, query)
    if not input_category:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail='Input category not found')

    input_category.deleted_status = True
    input_category.deleted_by = user
    input_category.last_updated_at = datetime.now()
    input_category.last_updated_by = user

    await db.commit()
    await db.refresh(input_category)
    return input_category
