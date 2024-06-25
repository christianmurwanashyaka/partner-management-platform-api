from datetime import datetime

import uuid
from fastapi import APIRouter, Depends, Request, status, HTTPException
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies.access_control import admin_access
from api.dependencies.auth import get_current_user
from db.database import get_db
from db.models import User, PaginatedResponse
from db.models.domain import SubDomainFunction, SubFunction
from helpers.db import get_first_item, check_if_exists, get_all_items
from schemas.sub_function import SubFunctionCreate, SubFunctionRead

router = APIRouter()


@router.post('/sub-functions', response_model=SubFunctionRead, dependencies=[Depends(admin_access)])
async def create_sub_function(
        request: Request,
        sub_function_form: SubFunctionCreate,
        db: AsyncSession = Depends(get_db)
):
    function_query = select(SubDomainFunction).filter(SubDomainFunction.uuid == sub_function_form.function_uuid)
    function = await get_first_item(db, function_query)
    if not function:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Sub domain function not found")

    existing_sub_function = await check_if_exists(
        SubFunction,
        db,
        name=sub_function_form.name,
        function_id=sub_function_form.function_uuid
    )

    if existing_sub_function:
        raise HTTPException(status.HTTP_409_CONFLICT, detail='Sub function with this name already exists within the same function')
    user = request.state.user.email
    new_sub_function = SubFunction(
        name=sub_function_form.name,
        description=sub_function_form.description,
        function_id=sub_function_form.function_uuid,
        created_by=user
    )

    db.add(new_sub_function)

    try:
        await db.commit()
        await db.refresh(new_sub_function)
        await db.refresh(function)
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    return new_sub_function


@router.get('/', response_model=PaginatedResponse[SubFunctionRead])
async def get_sub_functions(
        page: int = 1,
        page_size: int = 100,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    return await get_all_items(db, SubFunction, page=page, page_size=page_size)


@router.get('/{uuid}', response_model=SubFunctionRead)
async def get_sub_function(
        uuid: str,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    query = select(SubFunction).filter(SubFunction.uuid == uuid)
    sub_function = await get_first_item(db, query)
    if not sub_function:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Sub Function not found")
    return sub_function


@router.delete('/{uuid}', response_model=SubFunctionRead, dependencies=[Depends(admin_access)])
async def delete_sub_function(uuid: uuid.UUID, request: Request, db: AsyncSession = Depends(get_db)):
    user = request.state.user.email
    query = select(SubFunction).filter(SubFunction.uuid == uuid)
    sub_function = await get_first_item(db, query)
    if not sub_function:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail='Sub Function not found')
    sub_function.deleted_status = True
    sub_function.deleted_by = user
    sub_function.last_updated_at = datetime.now()
    sub_function.last_updated_by = user

    await db.commit()
    await db.refresh(sub_function)
    return sub_function
