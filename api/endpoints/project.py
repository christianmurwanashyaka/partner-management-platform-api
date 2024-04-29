from typing import Optional

import uuid
from fastapi import APIRouter, Request, Depends, HTTPException, status, Form, File, UploadFile
from sqlalchemy import func
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError
from sqlmodel.ext.asyncio.session import AsyncSession

from api.dependencies.access_control import partner_access, admin_access, swapteam_member_access
from api.dependencies.auth import get_current_user
from db.database import get_db
from db.models.organization import Organization
from db.models.pagination import PaginatedResponse
from db.models.project import Project, OperationalZone
from db.models.user import User
from helpers.db import check_if_exists, get_all_items, get_first_item, get_items_by_criteria
from schemas.project import ProjectRead, ProjectCreate, ProjectList
from utils.files import handle_upload_file

router = APIRouter()


@router.post('/', response_model=ProjectRead, dependencies=[Depends(partner_access)])
async def create_project(request: Request, project: ProjectCreate, db: AsyncSession = Depends(get_db)):
    user = request.state.user.email
    new_project = Project(
        name=project.name,
        description=project.description,
        domain_intervention_id=project.domain_intervention_id,
        budget_type_id=project.budget_type_id,
        planned_budget=project.planned_budget,
        start_date=project.start_date,
        end_date=project.end_date,
        organization_id=project.organization_id,
        funding_unit_id=project.funding_unit_id,
        funding_source_id=project.funding_source_id,
        created_by=user
    )
    try:
        db.add(new_project)
        await db.commit()
        await db.refresh(new_project)

        new_operational_zone = OperationalZone(
            project_id=new_project.uuid,
            provinces=project.operational_zone.provinces,
            districts=project.operational_zone.districts,
            created_by=user
        )

        db.add(new_operational_zone)
        await db.commit()
        await db.refresh(new_project)
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    return new_project


@router.get('/', response_model=PaginatedResponse[ProjectRead])
async def get_projects(
        page: int = 1,
        page_size: int = 100,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    if current_user.role in ['admin', 'swapteam_member']:
        total_items, projects = await get_all_items(db, Project, page=page, page_size=page_size, include=['organization'])
    elif current_user.role == 'partner':
        query = select(Project).join(Organization).filter(Organization.created_by == current_user.email)
        total_items = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar_one()
        projects = await get_items_by_criteria(db, query.offset((page - 1) * page_size).limit(page_size))
    else:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail='You are not authorized to perform this action')

    total_pages = (total_items + page_size - 1) // page_size

    return PaginatedResponse(
        page=page,
        page_size=page_size,
        total_items=total_items,
        total_pages=total_pages,
        data=projects
    )