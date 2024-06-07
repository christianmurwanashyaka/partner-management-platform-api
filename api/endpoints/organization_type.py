import uuid
from datetime import datetime

from fastapi import APIRouter, Request, Depends, HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.future import select

from api.dependencies.access_control import admin_access, partner_access, moh_staff_access
from api.dependencies.auth import get_current_user
from db.database import get_db
from db.models import User
from db.models.organization_type import OrganizationType
from db.models.pagination import PaginatedResponse
from schemas.organization_type import OrganizationTypeRead, OrganizationTypeCreate
from helpers.db import check_if_exists, get_all_items, get_first_item

router = APIRouter()


@router.post('/', response_model=OrganizationTypeRead, dependencies=[Depends(admin_access)])
async def create_organization_type(request: Request, organization_type: OrganizationTypeCreate, db: AsyncSession = Depends(get_db)):
    user = request.state.user.email

    if await check_if_exists(OrganizationType, db, name=organization_type.name):
        raise HTTPException(status.HTTP_409_CONFLICT, detail='Organization type with this name already exists')

    new_organization_type = OrganizationType(name=organization_type.name, description=organization_type.description, created_by=user)

    db.add(new_organization_type)
    await db.commit()
    await db.refresh(new_organization_type)
    return new_organization_type


@router.get('/', response_model=PaginatedResponse[OrganizationType])
async def get_organization_types(page: int = 1, page_size: int = 100, db: AsyncSession = Depends(get_db)):
    return await get_all_items(db, OrganizationType, page=page, page_size=page_size)


@router.get('/{uuid}', response_model=OrganizationTypeRead)
async def get_organization_type(uuid: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    query = select(OrganizationType).filter(OrganizationType.uuid == uuid)
    organization_type = await get_first_item(db, query)
    if not organization_type:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail='Organization type not found')
    return organization_type


@router.delete('/{uuid}', response_model=OrganizationTypeRead, dependencies=[Depends(admin_access)])
async def delete_organization_type(uuid: uuid.UUID, request: Request, db: AsyncSession = Depends(get_db)):
    user = request.state.user.email

    query = select(OrganizationType).filter(OrganizationType.uuid == uuid)
    organization_type = await get_first_item(db, query)
    if not organization_type:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail='Organization type not found')

    organization_type.deleted_status = True
    organization_type.deleted_by = user
    organization_type.last_updated_at = datetime.now()
    organization_type.last_updated_by = user

    await db.commit()
    await db.refresh(organization_type)
    return organization_type
