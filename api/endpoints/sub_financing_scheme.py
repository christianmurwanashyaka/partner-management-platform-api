from datetime import datetime

from fastapi import APIRouter, Depends, Request, HTTPException, status
from sqlalchemy import select
from sqlmodel.ext.asyncio.session import AsyncSession

from api.dependencies.access_control import admin_access
from api.dependencies.auth import get_current_user
from db.database import get_db
from db.models import (
    FinancingScheme,
    SubFinancingScheme,
    PaginatedResponse,
    UserRole,
    User,
)
from helpers.db import get_first_item, check_if_exists, get_all_items
from schemas.sub_financing_scheme import (
    SubFinancingSchemeList,
    SubFinancingSchemeCreate,
)

router = APIRouter()


@router.post(
    "/", response_model=SubFinancingSchemeList, dependencies=[Depends(admin_access)]
)
async def create_sub_financing_scheme(
    request: Request,
    sub_financing_scheme_data: SubFinancingSchemeCreate,
    db: AsyncSession = Depends(get_db),
):
    try:
        financing_scheme_query = select(FinancingScheme).filter(
            FinancingScheme.uuid == sub_financing_scheme_data.financing_scheme_uuid
        )
        financing_scheme = await get_first_item(db, financing_scheme_query)

        if not financing_scheme:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND, detail="Financing scheme not found"
            )
        existing_sub_financing_scheme = await check_if_exists(
            SubFinancingScheme,
            db,
            name=sub_financing_scheme_data.name,
            financing_scheme_uuid=sub_financing_scheme_data.financing_scheme_uuid,
        )
        if existing_sub_financing_scheme:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                detail="Sub financing scheme with this name already exists",
            )

        user = request.state.user.email
        new_sub_financing_scheme = SubFinancingScheme(
            name=sub_financing_scheme_data.name,
            description=sub_financing_scheme_data.description,
            financing_scheme_uuid=sub_financing_scheme_data.financing_scheme_uuid,
            created_by=user,
            sha_code=sub_financing_scheme_data.sha_code,
        )
        db.add(new_sub_financing_scheme)
        await db.commit()
        await db.refresh(new_sub_financing_scheme)
        return new_sub_financing_scheme
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/", response_model=PaginatedResponse[SubFinancingSchemeList])
async def get_sub_financing_schemes(
    page: int = 1,
    page_size: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        if current_user.role != UserRole.DATA_MANAGER:
            raise HTTPException(
                status_code=403, detail="Access denied. User must be a data manager."
            )
        return await get_all_items(
            db, SubFinancingScheme, page=page, page_size=page_size
        )
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/{uuid}", response_model=SubFinancingSchemeList)
async def get_sub_financing_scheme(
    uuid: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        if current_user.role != UserRole.DATA_MANAGER:
            raise HTTPException(
                status_code=403, detail="Access denied. User must be a data manager."
            )
        query = select(SubFinancingScheme).filter(SubFinancingScheme.uuid == uuid)
        sub_financing_scheme = await get_first_item(db, query)
        if not sub_financing_scheme:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND, detail="Sub financing scheme not found"
            )
        return sub_financing_scheme
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.delete(
    "/{uuid}",
    response_model=SubFinancingSchemeList,
    dependencies=[Depends(admin_access)],
)
async def delete_sub_financing_scheme(
    uuid: str, request: Request, db: AsyncSession = Depends(get_db)
):
    try:
        user = request.state.user.email

        query = select(SubFinancingScheme).filter(SubFinancingScheme.uuid == uuid)
        sub_financing_scheme = await get_first_item(db, query)
        if not sub_financing_scheme:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND, detail="Sub financing scheme not found"
            )

        sub_financing_scheme.deleted_status = True
        sub_financing_scheme.deleted_by = user
        sub_financing_scheme.last_updated_at = datetime.now()
        sub_financing_scheme.last_updated_by = user

        await db.commit()
        await db.refresh(sub_financing_scheme)
        return sub_financing_scheme
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
