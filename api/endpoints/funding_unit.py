from fastapi import APIRouter, Request, Depends, HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.future import select

from api.dependencies.access_control import admin_access
from db.database import get_db
from db.models.funding_unit import FundingUnit
from db.models.pagination import PaginatedResponse
from schemas.funding_unit import FundingUnitRead, FundingUnitCreate
from helpers.db import check_if_exists, get_all_items, get_first_item

router = APIRouter()


@router.post('/', response_model=FundingUnitRead, dependencies=[Depends(admin_access)])
async def create_funding_unit(request: Request, funding_unit: FundingUnitCreate, db: AsyncSession = Depends(get_db)):
    user = request.state.user.email

    if await check_if_exists(FundingUnit, db, name=funding_unit.name):
        raise HTTPException(status.HTTP_409_CONFLICT, detail='Funding unit with this name already exists')

    new_funding_unit = FundingUnit(name=funding_unit.name, description=funding_unit.description, created_by=user)

    db.add(new_funding_unit)
    await db.commit()
    await db.refresh(new_funding_unit)
    return new_funding_unit


@router.get('/', response_model=PaginatedResponse[FundingUnitRead], dependencies=[Depends(admin_access)])
async def get_funding_units(page: int = 1, page_size: int = 100, db: AsyncSession = Depends(get_db)):
    return await get_all_items(db, FundingUnit, page=page, page_size=page_size)


@router.get('/{uuid}', response_model=FundingUnitRead, dependencies=[Depends(admin_access)])
async def get_funding_unit(uuid: str, db: AsyncSession = Depends(get_db)):
    query = select(FundingUnit).filter(FundingUnit.uuid == uuid)
    funding_unit = await get_first_item(db, query)
    if not funding_unit:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail='Funding unit not found')
    return funding_unit
