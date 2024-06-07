import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Request, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from api.dependencies.access_control import admin_access
from api.dependencies.auth import get_current_user
from db.database import get_db
from db.models import SubDomain, User, PaginatedResponse
from db.models.domain import SubDomainFunction
from helpers.db import get_first_item, check_if_exists, get_all_items
from schemas.sub_domain_function import SubDomainFunctionRead, SubDomainFunctionCreate

router = APIRouter()


@router.post('/functions/', response_model=SubDomainFunctionRead, dependencies=[Depends(admin_access)])
async def create_subdomain_function(request: Request, sub_domain_function_form: SubDomainFunctionCreate,
                                    db: AsyncSession = Depends(get_db)):
    # Check if the parent sub_domain exists
    sub_domain_query = select(SubDomain).filter(SubDomain.uuid == sub_domain_function_form.sub_domain_uuid)
    sub_domain = await get_first_item(db, sub_domain_query)
    if not sub_domain:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail='SubDomain not found')

    # Check if a sub_domain_function with the same name already exists within the same sub_domain
    existing_subdomain_function = await check_if_exists(SubDomainFunction, db, name=sub_domain_function_form.name,
                                                        sub_domain_id=sub_domain_function_form.sub_domain_uuid)
    if existing_subdomain_function:
        raise HTTPException(status.HTTP_409_CONFLICT,
                            detail='SubDomainFunction with this name already exists within the same SubDomain')

    user = request.state.user.email
    new_subdomain_function = SubDomainFunction(
        name=sub_domain_function_form.name,
        description=sub_domain_function_form.description,
        sub_domain_id=sub_domain_function_form.sub_domain_uuid,
        created_by=user
    )

    db.add(new_subdomain_function)
    try:
        await db.commit()
        await db.refresh(new_subdomain_function)
        await db.refresh(sub_domain)
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    return new_subdomain_function


@router.get('/', response_model=PaginatedResponse[SubDomainFunctionRead])
async def get_sub_domain_functions(page: int = 1, page_size: int = 100, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    return await get_all_items(db, SubDomainFunction, page=page, page_size=page_size)


@router.get('/{uuid}', response_model=SubDomainFunctionRead)
async def get_sub_domain_function(uuid: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    query = select(SubDomainFunction).filter(SubDomainFunction.uuid == uuid)
    sub_domain_function = await get_first_item(db, query)
    if not sub_domain_function:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail='SubDomainFunction not found')
    return sub_domain_function


@router.delete('/{uuid}', response_model=SubDomainFunctionRead, dependencies=[Depends(admin_access)])
async def delete_sub_domain_function(uuid: uuid.UUID, request: Request, db: AsyncSession = Depends(get_db)):
    user = request.state.user.email
    query = select(SubDomainFunction).filter(SubDomainFunction.uuid == uuid)
    sub_domain_function = await get_first_item(db, query)
    if not sub_domain_function:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail='SubDomainFunction not found')
    sub_domain_function.deleted_status = True
    sub_domain_function.deleted_by = user
    sub_domain_function.last_updated_at = datetime.now()
    sub_domain_function.last_updated_by = user
    await db.commit()
    await db.refresh(sub_domain_function)
    return sub_domain_function
