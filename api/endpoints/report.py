import uuid
from math import ceil

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from api.dependencies.auth import get_current_user
from db.database import get_db
from db.models import User, UserRole, Activity, Project, MouDetail, MouApplication, MouApplicationStatus, InputDetail, \
    PaginatedResponse, ActivityDomain, Report, ReportActivity, ReportActivityStatus
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


@router.get('/data-manager/reported_activities')
async def get_reported_activities(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
        page: int = Query(1, ge=1, description='Page number'),
        page_size: int = Query(10, ge=1, le=100, description='Number of items per page')
):
    try:
        if current_user.role != UserRole.DATA_MANAGER:
            raise HTTPException(status_code=403, detail='Access denied. User must be a data manager')

        # Join with the Report table to filter by organization
        query = select(ReportActivity).join(Report).where(
            Report.organization_uuid == current_user.organization_uuid
        ).options(
            selectinload(ReportActivity.report),
            selectinload(ReportActivity.comments),
        )

        count_query = select(func.count()).select_from(query.subquery())
        total_items = await db.execute(count_query)
        total_items = total_items.scalar()
        total_pages = ceil(total_items / page_size)

        result = await db.execute(query.offset((page - 1) * page_size).limit(page_size))
        activities_data = result.scalars().all()

        activities_list = [
            {
                "uuid": str(activity.uuid),
                "report_uuid": str(activity.report_uuid),
                "reported_by": activity.reported_by,
                "executed_budget": activity.executed_budget,
                "actual_start_date": activity.actual_start_date.isoformat() if activity.actual_start_date else None,
                "actual_end_date": activity.actual_end_date.isoformat() if activity.actual_end_date else None,
                "status": activity.status.value,
                "accomplishments": activity.accomplishments,
                "comments": activity.comments,
                # Add other fields as needed
            }
            for activity in activities_data
        ]

        return {
            'page': page,
            'page_size': page_size,
            'total_pages': total_pages,
            'total_items': total_items,
            'items': activities_list
        }

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=f"An internal server error occurred: {str(e)}")


@router.post('/data-manager/reported_activity/{uuid}/approve')
async def approve_reported_activity(
        uuid: uuid.UUID,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    try:
        if current_user.role != UserRole.DATA_MANAGER:
            raise HTTPException(status_code=403, detail='Access denied. User must be a data manager')

        # Fetch the reported activity
        query = select(ReportActivity).where(ReportActivity.uuid == uuid)
        result = await db.execute(query)
        activity = result.scalar_one_or_none()

        if not activity:
            raise HTTPException(status_code=404, detail='Reported activity not found')

        # Check if the activity belongs to the user's organization
        report_query = select(Report).where(Report.uuid == activity.report_uuid)
        report_result = await db.execute(report_query)
        report = report_result.scalar_one_or_none()

        if not report or report.organization_uuid != current_user.organization_uuid:
            raise HTTPException(status_code=403, detail='Access denied. Activity does not belong to your organization')

        # Check if the activity is in PENDING status
        if activity.status != ReportActivityStatus.PENDING:
            raise HTTPException(status_code=400, detail='Only pending activities can be approved')

        # Update the status to APPROVED
        activity.status = ReportActivityStatus.APPROVED
        db.add(activity)
        await db.commit()
        await db.refresh(activity)

        return {
            "message": "Activity approved successfully",
            "activity": {
                "uuid": str(activity.uuid),
                "status": activity.status.value,
                "report_uuid": str(activity.report_uuid),
                # Include other relevant fields here
            }
        }

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        await db.rollback()
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=f"An internal server error occurred: {str(e)}")


@router.get('/data-manager/reports')
async def get_reports(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db), page: int = Query(1, ge=1, description='Page number'), page_size: int = Query(10, ge=1, le=100, description='Number of items per page')):
    try:
        if current_user.role != UserRole.DATA_MANAGER:
            raise HTTPException(status_code=403, detail='Access denied. User must be a data manager')

        query = select(Report).where(
            Report.organization_uuid == current_user.organization_uuid
        )

        count_query = select(func.count()).select_from(query.subquery())
        total_items = await db.execute(count_query)
        total_items = total_items.scalar()
        total_pages = ceil(total_items/page_size)

        result = await db.execute(query.offset((page-1) * page_size).limit(page_size))
        reports_data = result.scalars().all()

        reports_list = [
            {
                "uuid": report.uuid,
                "mou_application_uuid": str(report.mou_application_uuid),
                "reported_by": report.reported_by,
                "organization_uuid": str(report.organization_uuid),
                "reported_at": report.reported_at.isoformat() if report.reported_at else None,
                "project_uuid": str(report.project_uuid),
                "status": report.status.value,
            }
            for report in reports_data
        ]

        return {
            'page': page,
            'page_size': page_size,
            'total_pages': total_pages,
            'items': reports_list
        }
    except HTTPException as http_exc:
        raise http_exc

    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=f"An internal server error occurred: {str(e)}")


@router.get('/data-manager/report/{uuid}/activities')
async def get_report_activities(
        uuid: uuid.UUID,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
        page: int = Query(1, ge=1, description='Page number'),
        page_size: int = Query(10, ge=1, le=100, description='Number of items per page')
):
    try:
        if current_user.role != UserRole.DATA_MANAGER:
            raise HTTPException(status_code=403, detail='Access denied. User must be a data manager')

        # First, check if the report exists and belongs to the user's organization
        report_query = select(Report).where(
            Report.uuid == uuid,
            Report.organization_uuid == current_user.organization_uuid
        )
        report_result = await db.execute(report_query)
        report = report_result.scalar_one_or_none()

        if not report:
            raise HTTPException(status_code=404, detail='Report not found or access denied')

        # Query for activities associated with this report
        query = select(ReportActivity).where(
            ReportActivity.report_uuid == uuid
        ).options(selectinload(ReportActivity.comments))

        # Get total count for pagination
        count_query = select(func.count()).select_from(query.subquery())
        total_items = await db.execute(count_query)
        total_items = total_items.scalar()
        total_pages = ceil(total_items / page_size)

        # Execute the main query with pagination
        result = await db.execute(query.offset((page - 1) * page_size).limit(page_size))
        activities = result.scalars().all()

        activities_list = [
            {
                "uuid": str(activity.uuid),
                "reported_by": activity.reported_by,
                "executed_budget": float(activity.executed_budget),
                "actual_start_date": activity.actual_start_date.isoformat() if activity.actual_start_date else None,
                "actual_end_date": activity.actual_end_date.isoformat() if activity.actual_end_date else None,
                "status": activity.status.value,
                "accomplishments": activity.accomplishments,
                "comments_count": len(activity.comments),
                # Add other fields as needed
            }
            for activity in activities
        ]

        return {
            "report_uuid": str(report.uuid),
            "project_uuid": str(report.project_uuid),
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "total_items": total_items,
            "activities": activities_list
        }

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=f"An internal server error occurred: {str(e)}")
