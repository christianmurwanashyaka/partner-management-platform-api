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
from db.models.activity import Activity
from db.models.input_detail import InputDetail
from sqlalchemy.orm import selectinload
from db.models.organization import Organization
from db.models.pagination import PaginatedResponse
from db.models.project import Project, OperationalZone
from db.models.user import User
from helpers.db import check_if_exists, get_all_items, get_first_item, get_items_by_criteria
from schemas.activity import ActivityRead, ActivityCreate, ActivityList
from schemas.input import InputRead
from schemas.input_category import InputCategoryRead, InputCategoryList
from schemas.input_detail import InputDetailRead
from schemas.project import ProjectRead, ProjectCreate, ProjectList
from schemas.sub_domain import SubDomainRead
from utils.files import handle_upload_file

router = APIRouter()


# TODO: FIX SHOWING THE INPUT DETAILS TOO
@router.post('/', response_model=ActivityRead, dependencies=[Depends(partner_access)])
async def create_activity(request: Request, activity: ActivityCreate, db: AsyncSession = Depends(get_db)):
    user = request.state.user.email
    new_activity = Activity(
        project_id=activity.project_id,
        name=activity.name,
        implementer=activity.implementer,
        implementer_unit=activity.implementer_unit,
        fiscal_year=activity.fiscal_year,
        sub_domain_id=activity.sub_domain_id,
        created_by=user
    )
    db.add(new_activity)
    await db.commit()
    await db.refresh(new_activity)

    input_details = []
    for input_detail_data in activity.input_details:
        new_input_detail = InputDetail(
            activity_id=new_activity.uuid,
            input_category_id=input_detail_data.input_category_id,
            input_id=input_detail_data.input_id,
            budget=input_detail_data.budget,
            districts=input_detail_data.districts,
            provinces=input_detail_data.provinces,
            created_by=user
        )
        input_details.append(new_input_detail)

    db.add_all(input_details)
    try:
        await db.commit()
        activity = await db.get(Activity, new_activity.id, options=[
            selectinload(Activity.sub_domain)
        ])
        await db.refresh(activity)
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    return activity


@router.get('/', response_model=PaginatedResponse[ActivityList])
async def get_activities(
        page: int = 1,
        page_size: int = 100,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    if current_user.role in ['admin', 'swapteam_member']:
        paginated_response = await get_all_items(db, Activity, page=page, page_size=page_size)
    elif current_user.role == 'partner':
        query = select(Activity).filter(Activity.created_by == current_user.email)
        total_items = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar_one()
        activities = await get_items_by_criteria(db, query.offset((page - 1) * page_size).limit(page_size))
        total_pages = (total_items + page_size - 1) // page_size
        paginated_response = PaginatedResponse(
            page=page,
            page_size=page_size,
            total_items=total_items,
            total_pages=total_pages,
            data=activities
        )
    else:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail='You are not authorized to perform this action')

    return paginated_response


@router.get('/{uuid}/input_details', response_model=PaginatedResponse[InputDetailRead])
async def get_activity_input_details(
        uuid: uuid.UUID,
        page: int = 1,
        page_size: int = 100,
        db: AsyncSession = Depends(get_db)
):
    query = (select(InputDetail)
             .where(InputDetail.activity_id == uuid)
             .order_by(InputDetail.created_at.desc())
             .offset((page - 1) * page_size)
             .limit(page_size))

    input_details = await db.execute(query)
    input_details_list = input_details.scalars().all()

    if not input_details_list:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No input details found for this activity")

    total_items_query = select(func.count()).select_from(InputDetail).where(InputDetail.activity_id == uuid)
    total_items = (await db.execute(total_items_query)).scalar_one()
    total_pages = (total_items + page_size - 1) // page_size

    return PaginatedResponse(
        page=page,
        page_size=page_size,
        total_items=total_items,
        total_pages=total_pages,
        data=input_details_list
    )
