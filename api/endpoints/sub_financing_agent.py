from datetime import datetime

from fastapi import APIRouter, Depends, Request, HTTPException, status
from sqlalchemy import select
from sqlmodel.ext.asyncio.session import AsyncSession

from api.dependencies.access_control import admin_access
from api.dependencies.auth import get_current_user
from db.database import get_db
from db.models import (
    PaginatedResponse,
    User,
    FinancingAgent,
    SubFinancingAgent,
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
async def create_sub_financing_agent(
    request: Request,
    sub_financing_agent_data: SubFinancingSchemeCreate,
    db: AsyncSession = Depends(get_db),
):
    try:
        financing_agent_query = select(FinancingAgent).filter(
            FinancingAgent.uuid == sub_financing_agent_data.financing_scheme_uuid
        )
        financing_agent = await get_first_item(db, financing_agent_query)

        if not financing_agent:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND, detail="Financing agent not found"
            )
        existing_sub_financing_agent = await check_if_exists(
            SubFinancingAgent,
            db,
            name=sub_financing_agent_data.name,
            financing_agent_uuid=sub_financing_agent_data.financing_scheme_uuid,
        )
        if existing_sub_financing_agent:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                detail="Sub financing scheme with this name already exists",
            )

        user = request.state.user.email
        new_sub_financing_agent = SubFinancingAgent(
            name=sub_financing_agent_data.name,
            description=sub_financing_agent_data.description,
            financing_agent_uuid=sub_financing_agent_data.financing_scheme_uuid,
            created_by=user,
            sha_code=sub_financing_agent_data.sha_code,
        )
        db.add(new_sub_financing_agent)
        await db.commit()
        await db.refresh(new_sub_financing_agent)
        return new_sub_financing_agent
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/", response_model=PaginatedResponse[SubFinancingSchemeList])
async def get_sub_financing_agents(
    page: int = 1,
    page_size: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return await get_all_items(
            db, SubFinancingAgent, page=page, page_size=page_size
        )
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/{uuid}", response_model=SubFinancingSchemeList)
async def get_sub_financing_agent(
    uuid: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        query = select(SubFinancingAgent).filter(SubFinancingAgent.uuid == uuid)
        sub_financing_agent = await get_first_item(db, query)
        if not sub_financing_agent:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND, detail="Sub financing agent not found"
            )
        return sub_financing_agent
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

        query = select(SubFinancingAgent).filter(SubFinancingAgent.uuid == uuid)
        sub_financing_agent = await get_first_item(db, query)
        if not sub_financing_agent:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND, detail="Sub financing agent not found"
            )

        sub_financing_agent.deleted_status = True
        sub_financing_agent.deleted_by = user
        sub_financing_agent.last_updated_at = datetime.now()
        sub_financing_agent.last_updated_by = user

        await db.commit()
        await db.refresh(sub_financing_agent)
        return sub_financing_agent
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
