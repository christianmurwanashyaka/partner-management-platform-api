from math import ceil

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from api.dependencies.auth import get_current_user
from db.database import get_db
from db.models import User, UserRole, Activity, Project, MouDetail, MouApplication, MouApplicationStatus, InputDetail
from db.models.activity import ActivityStatus
from schemas.report import ActivityResponse, PaginatedActivityResponse, ActivityAssignment

router = APIRouter()


@router.get('/data_manager/activities', response_model=PaginatedActivityResponse)
async def get_data_manager_activities(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Number of items per page"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        if current_user.role != UserRole.DATA_MANAGER:
            raise HTTPException(status_code=403, detail="Access denied. User must be a data manager.")

        print(f"Fetching approved activities for user {current_user.email}, page {page}, page_size {page_size}")

        budget_subquery = (
            select(
                InputDetail.activity_id,
                func.sum(InputDetail.budget).label('planned_budget')
            )
            .group_by(InputDetail.activity_id)
            .subquery()
        )

        query = (
            select(Activity, Project.name.label('project_name'), Project.currency, budget_subquery.c.planned_budget)
            .join(Project, Activity.project_id == Project.uuid)
            .join(MouDetail, MouDetail.project_id == Project.uuid)
            .join(MouApplication, MouApplication.mou_detail_id == MouDetail.uuid)
            .outerjoin(budget_subquery, Activity.uuid == budget_subquery.c.activity_id)
            .where(
                (Project.organization_id == current_user.organization_uuid) &
                (MouApplication.status == MouApplicationStatus.APPROVED)
            )
            .options(joinedload(Activity.project))
            .order_by(Activity.created_at.desc())
        )

        count_query = select(func.count()).select_from(query.subquery())
        total_items = await db.execute(count_query)
        total_items = total_items.scalar()

        print(f"Total items: {total_items}")

        total_pages = ceil(total_items / page_size)

        if page > total_pages and total_pages > 0:
            raise HTTPException(status_code=404, detail=f"Page {page} does not exist. Total pages: {total_pages}")

        result = await db.execute(
            query.offset((page - 1) * page_size).limit(page_size)
        )
        activities_data = result.all()

        print(f"Retrieved {len(activities_data)} activities")

        activities = []
        for activity, project_name, currency, planned_budget in activities_data:
            activity_dict = activity.__dict__
            activity_dict['uuid'] = str(activity_dict['uuid'])  # Convert UUID to string
            activities.append(
                ActivityResponse(
                    **{**activity_dict,
                       'project_name': project_name,
                       'currency': currency,
                       'planned_budget': planned_budget or 0}
                )
            )

        return PaginatedActivityResponse(
            items=activities,
            total_items=total_items,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )

    except HTTPException as http_exc:
        print(f"HTTP exception occurred: {http_exc.detail}")
        raise http_exc

    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")
        raise HTTPException(status_code=500, detail=f"An internal server error occurred: {str(e)}")


@router.post('/data_manager/activities/assign')
async def assign_activities_to_data_reporter(
        activities: ActivityAssignment,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    if current_user.role != UserRole.DATA_MANAGER:
        raise HTTPException(status_code=403, detail="Access denied. User must be a data manager.")

    try:
        stmt = (
            update(Activity)
            .where(Activity.uuid.in_(activities.activity_uuid))
            .values(status=ActivityStatus.READY_FOR_REPORT)
            .execution_options(synchronize_session=False)
        )
        result = await db.execute(stmt)
        await db.commit()

        updated_count = result.rowcount
        if updated_count != len(activities.activity_uuid):
            print(f"Warning: only {updated_count} out of {len(activities.activity_uuid)} activities were updated.")

    except Exception as e:
        await db.rollback()
        print(f"An error occured while assigning activities: {str(e)}")
        raise HTTPException(status_code=500, detail=f"An internal server error occurred: {str(e)}")
    return {"message": f"{updated_count} activities assigned successfully"}


@router.get('/data-reporter/activities', response_model=PaginatedActivityResponse)
async def get_data_reporter_activities(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Number of items per page")
):
    try:
        if current_user.role != UserRole.DATA_REPORTER:
            raise HTTPException(status_code=403, detail="Access denied. User must be a data reporter.")
        query = (
            select(Activity, Project.name.label('project_name'), Project.currency)
            .join(Project, Activity.project_id == Project.uuid)
            .where(
                (Project.organization_id == current_user.organization_uuid) &
                (Activity.status == ActivityStatus.READY_FOR_REPORT)
            )
            .options(joinedload(Activity.project))
            .order_by(Activity.created_at.desc())
        )

        count_query = select(func.count()).select_from(query.subquery())
        total_items = await db.execute(count_query)
        total_items = total_items.scalar()

        total_pages = ceil(total_items / page_size)

        if page > total_pages and total_pages > 0:
            raise HTTPException(status_code=404, detail=f"Page {page} does not exist. Total pages: {total_pages}")

        result = await db.execute(
            query.offset((page - 1) * page_size).limit(page_size)
        )
        activities_data = result.all()

        activities = []
        for activity, project_name, currency in activities_data:
            activity_dict = activity.__dict__
            activity_dict['uuid'] = str(activity_dict['uuid'])  # Convert UUID to string
            activities.append(
                ActivityResponse(
                    **{**activity_dict,
                       'project_name': project_name,
                       'currency': currency}
                )
            )

        return PaginatedActivityResponse(
            items=activities,
            total_items=total_items,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )

    except HTTPException as http_exc:
        print(f"HTTP exception occurred: {http_exc.detail}")
        raise http_exc

    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")
        raise HTTPException(status_code=500, detail=f"An internal server error occurred: {str(e)}")


