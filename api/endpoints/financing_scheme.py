import uuid
from datetime import datetime

from fastapi import APIRouter, Request, HTTPException, status
from fastapi.params import Depends
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload
from sqlmodel.ext.asyncio.session import AsyncSession

from api.dependencies.access_control import admin_access
from api.dependencies.auth import get_current_user
from db.database import get_db
from db.models import (
    FinancingScheme,
    PaginatedResponse,
    User,
)
from helpers.db import (
    check_if_exists,
    get_all_items,
    get_first_item,
)
from schemas.financing_scheme import (
    FinancingSchemeRead,
    FinancingSchemeCreate,
    FinancingSchemeList,
)

router = APIRouter()


@router.post(
    "/", response_model=FinancingSchemeRead, dependencies=[Depends(admin_access)]
)
async def create_financing_scheme(
    request: Request,
    financing_scheme_data: FinancingSchemeCreate,
    db: AsyncSession = Depends(get_db),
):
    try:
        user = request.state.user.email

        if await check_if_exists(FinancingScheme, db, name=financing_scheme_data.name):
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                detail="Financing scheme with this name already exists",
            )

        new_financing_scheme = FinancingScheme(
            name=financing_scheme_data.name,
            description=financing_scheme_data.description,
            created_by=user,
            sha_code=financing_scheme_data.sha_code,
        )
        db.add(new_financing_scheme)
        await db.commit()
        await db.refresh(new_financing_scheme)
        return new_financing_scheme
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/", response_model=PaginatedResponse[FinancingSchemeList])
async def get_financing_schemes(
    page: int = 1,
    page_size: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return await get_all_items(db, FinancingScheme, page=page, page_size=page_size)
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/{uuid}", response_model=FinancingSchemeRead)
async def get_financing_scheme(
    uuid: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        query = (
            select(FinancingScheme)
            .filter(FinancingScheme.uuid == uuid)
            .options(joinedload(FinancingScheme.sub_financing_schemes))
        )
        result = await db.execute(query)

        financing_scheme = result.unique().scalar_one_or_none()

        if not financing_scheme:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND, detail="Financing scheme not found"
            )
        return financing_scheme
    except Exception as e:
        print("ERROR: ", e)
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.delete(
    "/{uuid}", response_model=FinancingSchemeRead, dependencies=[Depends(admin_access)]
)
async def delete_financing_scheme(
    uuid: uuid.UUID, request: Request, db: AsyncSession = Depends(get_db)
):
    try:
        user = request.state.user.email
        query = select(FinancingScheme).filter(FinancingScheme.uuid == uuid)
        financing_scheme = await get_first_item(db, query)

        if not financing_scheme:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND, detail="Financing scheme not found"
            )

        financing_scheme.deleted_status = True
        financing_scheme.deleted_by = user
        financing_scheme.last_updated_at = datetime.now()
        financing_scheme.last_updated_by = user

        await db.commit()
        await db.refresh(financing_scheme)
        return financing_scheme
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
