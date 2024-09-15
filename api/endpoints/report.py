import uuid
from math import ceil

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from api.dependencies.auth import get_current_user
from db.database import get_db
from db.models import User, UserRole, Activity, Project, MouDetail, MouApplication, MouApplicationStatus, InputDetail, \
    PaginatedResponse, ActivityDomain
from db.models.activity import ActivityStatus, ActivityReportingStatus
from db.models.user_activity import UserActivity
from helpers.activity import fetch_activities_for_projects
from schemas.project import ProjectList
from schemas.report import ActivityResponse, PaginatedActivityResponse, ActivityAssignment, ReportProjectActivityRead, \
    ProjectActivitiesResponse, PaginatedProjectActivitiesResponse

router = APIRouter()


@router.get('/data_manager/projects', response_model=PaginatedResponse[ProjectList])
async def get_data_manager_projects(
        page: int = Query(1, ge=1, description="Page number"),
        page_size: int = Query(10, ge=1, le=100, description="Number of items per page"),
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    try:
        if current_user.role != UserRole.DATA_MANAGER:
            raise HTTPException(status_code=403, detail="Access denied. User must be a data manager.")

        # Query for projects without loading activities
        query = (
            select(Project)
            .join(MouDetail, Project.uuid == MouDetail.project_id)
            .join(MouApplication, MouDetail.uuid == MouApplication.mou_detail_id)
            .where(
                Project.organization_id == current_user.organization_uuid,
                MouApplication.status == MouApplicationStatus.APPROVED
            )
        )

        # Paginate the results
        results = await db.execute(query.offset((page - 1) * page_size).limit(page_size))
        projects = results.scalars().all()

        # Fetch activities for all projects
        activities_by_project = await fetch_activities_for_projects(db, projects)

        # Convert to dictionaries
        projects_list = [
            ProjectList(
                uuid=project.uuid,
                name=project.name,
                description=project.description,
                duration=project.duration,
                currency=project.currency,
                fiscal_year_budgets=project.fiscal_year_budgets,
                total_budget=project.total_budget,
                activities=activities_by_project.get(project.uuid, [])
            ) for project in projects
        ]

        # Calculate total count
        total_count = await db.execute(select(func.count()).select_from(query))
        total_count = total_count.scalar()
        total_pages = (total_count + page_size - 1) // page_size

        return PaginatedResponse(
            data=projects_list,
            page=page,
            page_size=page_size,
            total_items=total_count,
            total_pages=total_pages
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


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

        total_pages = ceil(total_items / page_size)

        if page > total_pages and total_pages > 0:
            raise HTTPException(status_code=404, detail=f"Page {page} does not exist. Total pages: {total_pages}")

        result = await db.execute(
            query.offset((page - 1) * page_size).limit(page_size)
        )
        activities_data = result.all()

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
        activity_assignment_data: ActivityAssignment,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    if current_user.role != UserRole.DATA_MANAGER:
        raise HTTPException(status_code=403, detail="Access denied. User must be a data manager.")

    try:
        user_activities = [
            UserActivity(user_uuid=activity_assignment_data.user_uuid, activity_uuid=activity_uuid, created_by=current_user.email) for activity_uuid in activity_assignment_data.activity_uuid
        ]
        db.add_all(user_activities)
        await db.commit()

        stmt = (
            update(Activity)
            .where(Activity.uuid.in_(activity_assignment_data.activity_uuid))
            .values(report_status=ActivityReportingStatus.READY_FOR_REPORT)
            .execution_options(synchronize_session=False)
        )
        result = await db.execute(stmt)
        await db.commit()

        updated_count = result.rowcount
        if updated_count != len(activity_assignment_data.activity_uuid):
            print(f"Warning: only {updated_count} out of {len(activity_assignment_data.activity_uuid)} activities were updated.")

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"An internal server error occurred: {str(e)}")
    return {"message": f"{updated_count} activities assigned successfully"}


@router.get('/data-reporter/activities', response_model=PaginatedProjectActivitiesResponse)
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
            select(Activity, Project.name.label('project_name'), Project.uuid.label('project_uuid'), Project.currency)
            .join(Project, Activity.project_id == Project.uuid)
            .join(UserActivity, Activity.uuid == UserActivity.activity_uuid)
            .options(
                selectinload(Activity.input_details).selectinload(InputDetail.input_category),
                selectinload(Activity.input_details).selectinload(InputDetail.input),
                selectinload(Activity.domains).selectinload(ActivityDomain.domain_intervention),
                selectinload(Activity.domains).selectinload(ActivityDomain.sub_domain),
                selectinload(Activity.domains).selectinload(ActivityDomain.sub_domain_function),
                selectinload(Activity.domains).selectinload(ActivityDomain.sub_function),
            )
            .where(
                (Project.organization_id == current_user.organization_uuid) &
                (Activity.report_status == ActivityReportingStatus.READY_FOR_REPORT) &
                (UserActivity.user_uuid == current_user.uuid)
            )
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

        # Group activities by project
        grouped_activities = {}
        for activity, project_name, project_uuid, currency in activities_data:
            activity_dict = activity.__dict__
            activity_dict['uuid'] = str(activity_dict['uuid'])  # Convert UUID to string

            if project_uuid not in grouped_activities:
                grouped_activities[project_uuid] = {
                    'project_name': project_name,
                    'project_uuid': str(project_uuid),
                    'project_currency': currency,
                    'activities': []
                }

            grouped_activities[project_uuid]['activities'].append(
                ActivityResponse(
                    **{**activity_dict, 'currency': currency}
                )
            )

        items = [
            ProjectActivitiesResponse(**project_data)
            for project_data in grouped_activities.values()
        ]

        return PaginatedProjectActivitiesResponse(
            items=items,
            total_items=total_items,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )

    except HTTPException as http_exc:
        raise http_exc

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An internal server error occurred: {str(e)}")
