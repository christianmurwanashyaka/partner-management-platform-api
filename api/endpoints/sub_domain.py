from fastapi import APIRouter, Request, Depends, HTTPException, status
from sqlalchemy.orm import selectinload
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.future import select

from api.dependencies.access_control import admin_access, partner_access, moh_staff_access
from api.dependencies.auth import get_current_user
from db.database import get_db
from db.models import User
from db.models.domain import SubDomain, DomainIntervention
from db.models.pagination import PaginatedResponse
from schemas.sub_domain import SubDomainList, SubDomainCreate, SubDomainRead
from helpers.db import check_if_exists, get_all_items, get_first_item

router = APIRouter()


@router.post('/', response_model=SubDomainList, dependencies=[Depends(admin_access)])
async def create_subdomain(request: Request, sub_domain_form: SubDomainCreate, db: AsyncSession = Depends(get_db)):
    domain_query = select(DomainIntervention).filter(DomainIntervention.uuid == sub_domain_form.domain_uuid)
    domain = await get_first_item(db, domain_query)
    if not domain:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail='Domain not found')

    existing_subdomain = await check_if_exists(SubDomain, db, name=sub_domain_form.name, domain_id=sub_domain_form.domain_uuid)

    if existing_subdomain:
        raise HTTPException(status.HTTP_409_CONFLICT, detail='Subdomain with this name already exists')

    user = request.state.user.email
    new_subdomain = SubDomain(name=sub_domain_form.name, description=sub_domain_form.description, domain_id=sub_domain_form.domain_uuid, created_by=user)

    db.add(new_subdomain)
    try:
        await db.commit()
        await db.refresh(new_subdomain)
        await db.refresh(domain)
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    return new_subdomain


@router.get('/', response_model=PaginatedResponse[SubDomainList])
async def get_all_sub_domains(page: int = 1, page_size: int = 100, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    return await get_all_items(db, SubDomain, page=page, page_size=page_size)


@router.get('/{uuid}', response_model=SubDomainRead)
async def get_sub_domain_details(uuid: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    query = select(SubDomain).options(selectinload(SubDomain.functions)).filter(SubDomain.uuid == uuid)
    subdomain = await get_first_item(db, query)
    if not subdomain:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail='SubDomain not found')
    return subdomain
