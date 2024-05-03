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
from schemas.project import ProjectRead, ProjectCreate, ProjectList
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
        fiscal_year=activity.fiscal_year,
        sub_domain_id=activity.sub_domain_id,
        districts=activity.districts,
        provinces=activity.provinces,
        created_by=user
    )
    try:
        db.add(new_activity)
        await db.commit()
        await db.refresh(new_activity)

        input_details = []
        for input_detail_data in activity.input_details:
            input_detail = InputDetail(
                activity_id=new_activity.uuid,
                input_category_id=input_detail_data.input_category_id,
                input_id=input_detail_data.input_id,
                budget=input_detail_data.budget,
                created_by=user
            )
            input_details.append(input_detail)

        db.add_all(input_details)
        await db.commit()
        activity = await db.get(Activity, new_activity.id, options=[
            selectinload(Activity.sub_domain),
            selectinload(Activity.input_details).selectinload(InputDetail.input_category),
            selectinload(Activity.input_details).selectinload(InputDetail.input)
        ])
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    return activity


@router.get('/', response_model=PaginatedResponse[ActivityList], dependencies=[Depends(admin_access)])
async def get_activities(page: int = 1, page_size: int = 100, db: AsyncSession = Depends(get_db)):
    return await get_all_items(db, Activity, page=page, page_size=page_size)

