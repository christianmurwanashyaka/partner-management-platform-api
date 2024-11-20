from datetime import datetime

from fastapi import APIRouter, Depends, Request, HTTPException, status
from sqlalchemy import select
from sqlmodel.ext.asyncio.session import AsyncSession

from api.dependencies.access_control import admin_access
from api.dependencies.auth import get_current_user
from db.database import get_db
from db.models import (
    PaginatedResponse,
    UserRole,
    User,
    HealthCareProvider,
    SubHealthCareProvider,
)
from helpers.db import check_if_exists, get_first_item, get_all_items
from schemas.sub_financing_scheme import (
    SubFinancingSchemeList,
    SubFinancingSchemeCreate,
)

router = APIRouter()


@router.post(
    "/", response_model=SubFinancingSchemeList, dependencies=[Depends(admin_access)]
)
async def create_sub_health_care_provider(
    request: Request,
    sub_health_care_provider_data: SubFinancingSchemeCreate,
    db: AsyncSession = Depends(get_db),
):
    try:
        health_care_provider_query = select(HealthCareProvider).filter(
            HealthCareProvider.uuid
            == sub_health_care_provider_data.financing_scheme_uuid
        )
        health_care_provider = await get_first_item(db, health_care_provider_query)

        if not health_care_provider:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND, detail="Health care provider not found"
            )
        existing_health_care_provider = await check_if_exists(
            SubHealthCareProvider,
            db,
            name=sub_health_care_provider_data.name,
            health_care_provider_uuid=sub_health_care_provider_data.financing_scheme_uuid,
        )
        if existing_health_care_provider:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                detail="Health care provider with this name already exists",
            )

        user = request.state.user.email
        new_sub_health_care_provider = SubHealthCareProvider(
            name=sub_health_care_provider_data.name,
            description=sub_health_care_provider_data.description,
            health_care_provider_uuid=sub_health_care_provider_data.financing_scheme_uuid,
            created_by=user,
            sha_code=sub_health_care_provider_data.sha_code,
        )
        db.add(new_sub_health_care_provider)
        await db.commit()
        await db.refresh(new_sub_health_care_provider)
        return new_sub_health_care_provider
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/", response_model=PaginatedResponse[SubFinancingSchemeList])
async def get_sub_health_care_providers(
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
            db, SubHealthCareProvider, page=page, page_size=page_size
        )
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/{uuid}", response_model=SubFinancingSchemeList)
async def get_sub_health_care_provider(
    uuid: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        if current_user.role != UserRole.DATA_MANAGER:
            raise HTTPException(
                status_code=403, detail="Access denied. User must be a data manager."
            )
        query = select(SubHealthCareProvider).filter(SubHealthCareProvider.uuid == uuid)
        sub_health_care_provider = await get_first_item(db, query)
        if not sub_health_care_provider:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND, detail="Sub health care provider not found"
            )
        return sub_health_care_provider
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.delete(
    "/{uuid}",
    response_model=SubFinancingSchemeList,
    dependencies=[Depends(admin_access)],
)
async def delete_sub_health_care_provider(
    uuid: str, request: Request, db: AsyncSession = Depends(get_db)
):
    try:
        user = request.state.user.email

        query = select(SubHealthCareProvider).filter(SubHealthCareProvider.uuid == uuid)
        sub_health_care_provider = await get_first_item(db, query)
        if not sub_health_care_provider:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND, detail="Sub health care provider not found"
            )

        sub_health_care_provider.deleted_status = True
        sub_health_care_provider.deleted_by = user
        sub_health_care_provider.last_updated_at = datetime.now()
        sub_health_care_provider.last_updated_by = user

        await db.commit()
        await db.refresh(sub_health_care_provider)
        return sub_health_care_provider
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
