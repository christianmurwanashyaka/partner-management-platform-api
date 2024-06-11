from datetime import datetime

import uuid
from fastapi import APIRouter, Request, Depends, HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.future import select

from api.dependencies.access_control import admin_access, partner_access, moh_staff_access
from api.dependencies.auth import get_current_user
from db.database import get_db
from db.models import User
from db.models.input_category import Input, InputCategory
from db.models.pagination import PaginatedResponse
from schemas.input import InputRead, InputCreate
from helpers.db import check_if_exists, get_all_items, get_first_item

router = APIRouter()


@router.post('/', response_model=InputRead, dependencies=[Depends(admin_access)])
async def create_input(request: Request, input_form: InputCreate, db: AsyncSession = Depends(get_db)):
    category_query = select(InputCategory).filter(InputCategory.uuid == input_form.input_category_uuid)
    category = await get_first_item(db, category_query)
    if not category:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail='Category not found')

    existing_input = await check_if_exists(Input, db, name=input_form.name, category_id=input_form.input_category_uuid)

    if existing_input:
        raise HTTPException(status.HTTP_409_CONFLICT, detail='Input with this name already exists')

    user = request.state.user.email
    new_input = Input(name=input_form.name, description=input_form.description, category_id=input_form.input_category_uuid, created_by=user)

    db.add(new_input)
    try:
        await db.commit()
        await db.refresh(new_input)
        await db.refresh(category)
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    return new_input


@router.get('/', response_model=PaginatedResponse[InputRead])
async def get_inputs(page: int = 1, page_size: int = 100, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    return await get_all_items(db, Input, page=page, page_size=page_size)


@router.delete('/{uuid}', response_model=InputRead, dependencies=[Depends(admin_access)])
async def delete_input(uuid: uuid.UUID, request: Request, db: AsyncSession = Depends(get_db)):
    user = request.state.user.email
    query = select(Input).filter(Input.uuid == uuid)
    input = await get_first_item(db, query)
    if not input:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail='Input not found')

    input.deleted_status = True
    input.deleted_by = user
    input.last_updated_at = datetime.now()
    input.last_updated_by = user

    await db.commit()
    await db.refresh(input)
    return input
