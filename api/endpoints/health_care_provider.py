import uuid
from datetime import datetime

from fastapi import APIRouter, Request, HTTPException, status
from fastapi.params import Depends
from sqlalchemy.future import select
from sqlmodel.ext.asyncio.session import AsyncSession

from api.dependencies.access_control import admin_access
from api.dependencies.auth import get_current_user
from db.database import get_db
from db.models import (
    PaginatedResponse,
    User,
    UserRole,
    HealthCareProvider,
    SubHealthCareProvider,
)
from helpers.db import (
    check_if_exists,
    get_all_items,
    get_joined_details_by_uuid,
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
async def create_health_care_provider(
    request: Request,
    health_care_provider_data: FinancingSchemeCreate,
    db: AsyncSession = Depends(get_db),
):
    try:
        user = request.state.user.email

        if await check_if_exists(
            HealthCareProvider, db, name=health_care_provider_data.name
        ):
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                detail="Health care provider with this name already exists",
            )

        new_health_care_provider = HealthCareProvider(
            name=health_care_provider_data.name,
            description=health_care_provider_data.description,
            created_by=user,
            sha_code=health_care_provider_data.sha_code,
        )
        db.add(new_health_care_provider)
        await db.commit()
        await db.refresh(new_health_care_provider)
        return new_health_care_provider
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/", response_model=PaginatedResponse[FinancingSchemeList])
async def get_health_care_providers(
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
            db, HealthCareProvider, page=page, page_size=page_size
        )
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/{uuid}", response_model=FinancingSchemeRead)
async def get_health_care_provider(
    uuid: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        if current_user.role != UserRole.DATA_MANAGER:
            raise HTTPException(
                status_code=403, detail="Access denied. User must be a data manager."
            )

        health_care_provider = await get_joined_details_by_uuid(
            db=db,
            model=HealthCareProvider,
            alias_model=SubHealthCareProvider,
            join_condition=lambda alias: alias.health_care_provider_uuid
            == HealthCareProvider.uuid,
            uuid=uuid,
            relationship_option=HealthCareProvider.sub_health_care_providers,
        )
        if not health_care_provider:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND, detail="Health care provider not found"
            )
        return health_care_provider
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.delete(
    "/{uuid}", response_model=FinancingSchemeRead, dependencies=[Depends(admin_access)]
)
async def delete_health_care_provider(
    uuid: uuid.UUID, request: Request, db: AsyncSession = Depends(get_db)
):
    try:
        user = request.state.user.email
        query = select(HealthCareProvider).filter(HealthCareProvider.uuid == uuid)
        health_care_provider = await get_first_item(db, query)

        if not health_care_provider:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND, detail="Health care provider not found"
            )

        health_care_provider.deleted_status = True
        health_care_provider.deleted_by = user
        health_care_provider.last_updated_at = datetime.now()
        health_care_provider.last_updated_by = user

        await db.commit()
        await db.refresh(health_care_provider)
        return health_care_provider
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
