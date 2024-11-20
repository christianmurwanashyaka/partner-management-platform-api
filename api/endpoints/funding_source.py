from datetime import datetime

import uuid
from fastapi import APIRouter, Request, Depends, HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.future import select

from api.dependencies.access_control import admin_access
from db.database import get_db
from db.models.funding_source import FundingSource
from db.models.pagination import PaginatedResponse
from schemas.funding_source import FundingSourceRead, FundingSourceCreate
from helpers.db import check_if_exists, get_all_items, get_first_item

router = APIRouter()


@router.post(
    "/", response_model=FundingSourceRead, dependencies=[Depends(admin_access)]
)
async def create_funding_source(
    request: Request,
    funding_source: FundingSourceCreate,
    db: AsyncSession = Depends(get_db),
):
    user = request.state.user.email

    if await check_if_exists(FundingSource, db, name=funding_source.name):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="Funding source with this name already exists",
        )

    funding_source = FundingSource(
        name=funding_source.name,
        description=funding_source.description,
        created_by=user,
    )

    db.add(funding_source)
    await db.commit()
    await db.refresh(funding_source)
    return funding_source


@router.get("/", response_model=PaginatedResponse[FundingSource])
async def get_funding_sources(
    page: int = 1, page_size: int = 100, db: AsyncSession = Depends(get_db)
):
    return await get_all_items(db, FundingSource, page=page, page_size=page_size)


@router.get("/{uuid}", response_model=FundingSourceRead)
async def get_funding_source(uuid: str, db: AsyncSession = Depends(get_db)):
    query = select(FundingSource).filter(FundingSource.uuid == uuid)
    funding_source = await get_first_item(db, query)
    if not funding_source:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, detail="Funding source not found"
        )
    return funding_source


@router.delete(
    "/{uuid}", response_model=FundingSourceRead, dependencies=[Depends(admin_access)]
)
async def delete_funding_source(
    uuid: uuid.UUID, request: Request, db: AsyncSession = Depends(get_db)
):
    user = request.state.user.email

    query = select(FundingSource).filter(FundingSource.uuid == uuid)
    funding_source = await get_first_item(db, query)
    if not funding_source:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, detail="Funding source not found"
        )

    funding_source.deleted_status = True
    funding_source.deleted_by = user
    funding_source.last_updated_at = datetime.now()
    funding_source.last_updated_by = user

    await db.commit()
    await db.refresh(funding_source)
    return funding_source
