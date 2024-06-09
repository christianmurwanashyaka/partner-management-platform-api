import uuid
from datetime import datetime

from fastapi import APIRouter, Request, Depends, HTTPException, status
from sqlalchemy.orm import selectinload, joinedload, aliased, contains_eager
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.future import select

from api.dependencies.access_control import admin_access, partner_access, moh_staff_access
from api.dependencies.auth import get_current_user
from db.database import get_db
from db.models import User
from db.models.domain import DomainIntervention, SubDomain
from db.models.pagination import PaginatedResponse
from schemas.domain_intervention import DomainInterventionRead, DomainInterventionList, DomainInterventionCreate
from helpers.db import check_if_exists, get_all_items, get_first_item, get_joined_details_by_uuid

router = APIRouter()


@router.post('/', response_model=DomainInterventionRead, dependencies=[Depends(admin_access)])
async def create_domain_intervention(request: Request, domain_intervention: DomainInterventionCreate, db: AsyncSession = Depends(get_db)):
    user = request.state.user.email

    if await check_if_exists(DomainIntervention, db, name=domain_intervention.name):
        raise HTTPException(status.HTTP_409_CONFLICT, detail='Domain intervention with this name already exists')

    new_domain_intervention = DomainIntervention(name=domain_intervention.name, description=domain_intervention.description, created_by=user)

    db.add(new_domain_intervention)
    try:
        await db.commit()
        await db.refresh(new_domain_intervention)
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    return new_domain_intervention


@router.get('/', response_model=PaginatedResponse[DomainInterventionList])
async def get_domain_interventions(page: int = 1, page_size: int = 100, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    return await get_all_items(db, DomainIntervention, page=page, page_size=page_size)


@router.get('/{uuid}', response_model=DomainInterventionRead)
async def get_domain_intervention(uuid: str, db: AsyncSession = Depends(get_db),
                                  current_user: User = Depends(get_current_user)):
    domain_intervention = await get_joined_details_by_uuid(
        db=db,
        model=DomainIntervention,
        alias_model=SubDomain,
        join_condition=lambda alias: alias.domain_id == DomainIntervention.uuid,
        uuid=uuid,
        relationship_option=DomainIntervention.subdomains
    )

    if not domain_intervention:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail='Domain intervention not found')

    return domain_intervention


@router.delete('/{uuid}', response_model=DomainInterventionRead, dependencies=[Depends(admin_access)])
async def delete_domain_intervention(uuid: uuid.UUID, request: Request, db: AsyncSession = Depends(get_db)):
    user = request.state.user.email

    query = select(DomainIntervention).filter(DomainIntervention.uuid == uuid)
    domain_intervention = await get_first_item(db, query)
    if not domain_intervention:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail='Domain intervention not found')

    domain_intervention.deleted_status = True
    domain_intervention.deleted_by = user
    domain_intervention.last_updated_at = datetime.now()
    domain_intervention.last_updated_by = user

    await db.commit()
    await db.refresh(domain_intervention)
    return domain_intervention
