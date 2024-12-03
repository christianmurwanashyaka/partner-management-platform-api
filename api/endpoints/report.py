import uuid
from datetime import datetime
from math import ceil

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from api.dependencies.auth import get_current_user
from db.database import get_db
from db.models import (
    User,
    UserRole,
    Activity,
    Project,
    MouDetail,
    MouApplication,
    MouApplicationStatus,
    InputDetail,
    PaginatedResponse,
    ActivityDomain,
    Report,
    ReportActivity,
    ReportActivityStatus,
    ReportStatus,
    Organization,
    Document,
    DocumentType,
)
from db.models.activity import ActivityReportingStatus
from db.models.user_activity import UserActivity
from helpers.activity import fetch_activities_for_projects
from schemas.project import ProjectList
from schemas.report import (
    ActivityResponse,
    PaginatedActivityResponse,
    ActivityAssignment,
    ProjectActivitiesResponse,
    PaginatedProjectActivitiesResponse,
    ReportedActivityResponse,
    PaginatedReportedActivityResponse,
    ReportedActivityProjectResponse,
    PaginatedReportResponse,
    ReportResponse,
)
from service.report_activity import ReportActivityService
from utils.files import generate_implementation_plan

router = APIRouter()


@router.get("/data_manager/projects", response_model=PaginatedResponse[ProjectList])
async def get_data_manager_projects(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Number of items per page"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        if current_user.role != UserRole.DATA_MANAGER:
            raise HTTPException(
                status_code=403, detail="Access denied. User must be a data manager."
            )

        # Query for projects without loading activities
        query = (
            select(Project)
            .join(MouDetail, Project.uuid == MouDetail.project_id)
            .join(MouApplication, MouDetail.uuid == MouApplication.mou_detail_id)
            .where(
                Project.organization_id == current_user.organization_uuid,
                MouApplication.status == MouApplicationStatus.APPROVED,
            )
        )

        # Paginate the results
        results = await db.execute(
            query.offset((page - 1) * page_size).limit(page_size)
        )
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
                activities=activities_by_project.get(project.uuid, []),
            )
            for project in projects
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
            total_pages=total_pages,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/data_manager/activities", response_model=PaginatedActivityResponse)
async def get_data_manager_activities(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Number of items per page"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        if current_user.role != UserRole.DATA_MANAGER:
            raise HTTPException(
                status_code=403, detail="Access denied. User must be a data manager."
            )

        budget_subquery = (
            select(
                InputDetail.activity_id,
                func.sum(InputDetail.budget).label("planned_budget"),
            )
            .group_by(InputDetail.activity_id)
            .subquery()
        )

        query = (
            select(
                Activity,
                Project.name.label("project_name"),
                Project.currency,
                budget_subquery.c.planned_budget,
            )
            .join(Project, Activity.project_id == Project.uuid)
            .join(MouDetail, MouDetail.project_id == Project.uuid)
            .join(MouApplication, MouApplication.mou_detail_id == MouDetail.uuid)
            .outerjoin(budget_subquery, Activity.uuid == budget_subquery.c.activity_id)
            .where(
                (Project.organization_id == current_user.organization_uuid)
                & (MouApplication.status == MouApplicationStatus.APPROVED)
            )
            .options(joinedload(Activity.project))
            .order_by(Activity.created_at.desc())
        )

        count_query = select(func.count()).select_from(query.subquery())
        total_items = await db.execute(count_query)
        total_items = total_items.scalar()

        total_pages = ceil(total_items / page_size)

        if page > total_pages and total_pages > 0:
            raise HTTPException(
                status_code=404,
                detail=f"Page {page} does not exist. Total pages: {total_pages}",
            )

        result = await db.execute(query.offset((page - 1) * page_size).limit(page_size))
        activities_data = result.all()

        activities = []
        for activity, project_name, currency, planned_budget in activities_data:
            activity_dict = activity.__dict__
            activity_dict["uuid"] = str(activity_dict["uuid"])  # Convert UUID to string
            activities.append(
                ActivityResponse(
                    **{
                        **activity_dict,
                        "project_name": project_name,
                        "currency": currency,
                        "planned_budget": planned_budget or 0,
                    }
                )
            )

        return PaginatedActivityResponse(
            items=activities,
            total_items=total_items,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    except HTTPException as http_exc:
        print(f"HTTP exception occurred: {http_exc.detail}")
        raise http_exc

    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"An internal server error occurred: {str(e)}"
        )


@router.post("/data_manager/activities/assign")
async def assign_activities_to_data_reporter(
    activity_assignment_data: ActivityAssignment,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.DATA_MANAGER:
        raise HTTPException(
            status_code=403, detail="Access denied. User must be a data manager."
        )

    try:
        # Check if any of the activities are already assigned to the user
        existing_assignments_query = (
            select(UserActivity)
            .where(UserActivity.user_uuid == activity_assignment_data.user_uuid)
            .where(
                UserActivity.activity_uuid.in_(activity_assignment_data.activity_uuid)
            )
        )
        existing_assignments = (
            (await db.execute(existing_assignments_query)).scalars().all()
        )

        if existing_assignments:
            existing_activities = [
                assignment.activity_uuid for assignment in existing_assignments
            ]
            raise HTTPException(
                status_code=400,
                detail=f"User already assigned to activities: {existing_activities}",
            )

        # Assign activities to the user
        user_activities = [
            UserActivity(
                user_uuid=activity_assignment_data.user_uuid,
                activity_uuid=activity_uuid,
                created_by=current_user.email,
            )
            for activity_uuid in activity_assignment_data.activity_uuid
        ]
        db.add_all(user_activities)
        await db.commit()

        # Update the activity reporting status
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
            print(
                f"Warning: only {updated_count} out of {len(activity_assignment_data.activity_uuid)} activities were updated."
            )

    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500, detail=f"An internal server error occurred: {str(e)}"
        )

    return {"message": f"{updated_count} activities assigned successfully"}


@router.get(
    "/data-reporter/activities", response_model=PaginatedProjectActivitiesResponse
)
async def get_data_reporter_activities(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Number of items per page"),
):
    try:
        if current_user.role != UserRole.DATA_REPORTER:
            raise HTTPException(
                status_code=403, detail="Access denied. User must be a data reporter."
            )

        query = (
            select(
                Activity,
                Project.name.label("project_name"),
                Project.uuid.label("project_uuid"),
                Project.currency,
            )
            .join(Project, Activity.project_id == Project.uuid)
            .join(UserActivity, Activity.uuid == UserActivity.activity_uuid)
            .options(
                selectinload(Activity.input_details).selectinload(
                    InputDetail.input_category
                ),
                selectinload(Activity.input_details).selectinload(InputDetail.input),
                selectinload(Activity.domains).selectinload(
                    ActivityDomain.domain_intervention
                ),
                selectinload(Activity.domains).selectinload(ActivityDomain.sub_domain),
                selectinload(Activity.domains).selectinload(
                    ActivityDomain.sub_domain_function
                ),
                selectinload(Activity.domains).selectinload(
                    ActivityDomain.sub_function
                ),
            )
            .where(
                (Project.organization_id == current_user.organization_uuid)
                & (Activity.report_status == ActivityReportingStatus.READY_FOR_REPORT)
                & (UserActivity.user_uuid == current_user.uuid)
            )
            .order_by(Activity.created_at.desc())
        )

        count_query = select(func.count()).select_from(query.subquery())
        total_items = await db.execute(count_query)
        total_items = total_items.scalar()

        total_pages = ceil(total_items / page_size)

        if page > total_pages and total_pages > 0:
            raise HTTPException(
                status_code=404,
                detail=f"Page {page} does not exist. Total pages: {total_pages}",
            )

        result = await db.execute(query.offset((page - 1) * page_size).limit(page_size))
        activities_data = result.all()

        # Group activities by project
        grouped_activities = {}
        for activity, project_name, project_uuid, currency in activities_data:
            activity_dict = activity.__dict__
            activity_dict["uuid"] = str(activity_dict["uuid"])  # Convert UUID to string

            if project_uuid not in grouped_activities:
                grouped_activities[project_uuid] = {
                    "project_name": project_name,
                    "project_uuid": str(project_uuid),
                    "project_currency": currency,
                    "activities": [],
                }

            grouped_activities[project_uuid]["activities"].append(
                ActivityResponse(**{**activity_dict, "currency": currency})
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
            total_pages=total_pages,
        )

    except HTTPException as http_exc:
        raise http_exc

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"An internal server error occurred: {str(e)}"
        )


@router.get(
    "/data-manager/reported_activities",
    response_model=PaginatedReportedActivityResponse,
)
async def get_reported_activities(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Number of items per page"),
):
    try:
        if current_user.role != UserRole.DATA_MANAGER:
            raise HTTPException(
                status_code=403, detail="Access denied. User must be a data manager"
            )

        query = (
            select(ReportActivity, Project, Activity)
            .join(Report, ReportActivity.report_uuid == Report.uuid)
            .join(Project, Report.project_uuid == Project.uuid)
            .join(
                Activity,
                and_(
                    Activity.uuid == ReportActivity.activity_uuid,
                    Activity.project_id == Project.uuid,
                    Activity.report_uuid == Report.uuid,
                ),
            )
            .options(
                selectinload(ReportActivity.comments),
                selectinload(Activity.input_details).joinedload(
                    InputDetail.input_category
                ),
                selectinload(Activity.input_details).joinedload(InputDetail.input),
                selectinload(Activity.domains).joinedload(
                    ActivityDomain.domain_intervention
                ),
                selectinload(Activity.domains).joinedload(ActivityDomain.sub_domain),
                selectinload(Activity.domains).joinedload(
                    ActivityDomain.sub_domain_function
                ),
                selectinload(Activity.domains).joinedload(ActivityDomain.sub_function),
            )
            .where(Report.organization_uuid == current_user.organization_uuid)
            .order_by(ReportActivity.created_at.desc())
        )

        count_query = select(func.count()).select_from(query.subquery())
        total_items = await db.execute(count_query)
        total_items = total_items.scalar()
        total_pages = ceil(total_items / page_size)

        if page > total_pages and total_pages > 0:
            raise HTTPException(
                status_code=404,
                detail=f"Page {page} does not exist. Total pages: {total_pages}",
            )

        result = await db.execute(query.offset((page - 1) * page_size).limit(page_size))
        activities_data = result.all()

        # Group activities by project
        grouped_activities = {}
        for report_activity, project, activity in activities_data:
            activity_dict = ReportedActivityResponse(
                # Fields from Activity
                uuid=str(activity.uuid),
                name=activity.name,
                description=activity.description,
                start_date=activity.start_date,
                end_date=activity.end_date,
                implementer=activity.implementer,
                implementer_unit=activity.implementer_unit,
                fiscal_year=activity.fiscal_year,
                project_name=project.name,
                planned_budget=(
                    sum(detail.budget for detail in activity.input_details)
                    if activity.input_details
                    else None
                ),
                currency=project.currency,
                status=activity.status,
                report_status=activity.report_status,
                input_details=[
                    {
                        "uuid": str(detail.uuid),
                        "category": detail.input_category.name,
                        "input": detail.input.name,
                        "budget": detail.budget,
                        "district": detail.district,
                        "province": detail.province,
                    }
                    for detail in activity.input_details
                ],
                domains=[
                    {
                        "uuid": str(domain.uuid),
                        "domain_intervention": domain.domain_intervention.name,
                        "sub_domain": domain.sub_domain.name,
                        "sub_domain_function": domain.sub_domain_function.name,
                        "sub_function": domain.sub_function.name,
                    }
                    for domain in activity.domains
                ],
                # Fields from ReportActivity
                report_uuid=str(report_activity.report_uuid),
                reported_by=report_activity.reported_by,
                executed_budget=report_activity.executed_budget,
                actual_start_date=(
                    report_activity.actual_start_date.date()
                    if report_activity.actual_start_date
                    else None
                ),
                actual_end_date=(
                    report_activity.actual_end_date.date()
                    if report_activity.actual_end_date
                    else None
                ),
                report_activity_status=report_activity.status,
                report_activity_uuid=str(report_activity.uuid),
                accomplishments=report_activity.accomplishments,
                comments=[
                    {
                        "uuid": str(comment.uuid),
                        "content": comment.content,
                        "created_at": comment.created_at,
                    }
                    for comment in report_activity.comments
                ],
            )

            if project.uuid not in grouped_activities:
                grouped_activities[project.uuid] = ReportedActivityProjectResponse(
                    project_name=project.name,
                    project_uuid=str(project.uuid),
                    project_currency=project.currency,
                    activities=[],
                )

            grouped_activities[project.uuid].activities.append(activity_dict)

        items = list(grouped_activities.values())

        return PaginatedReportedActivityResponse(
            items=items,
            total_items=total_items,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(
            status_code=500, detail=f"An internal server error occurred: {str(e)}"
        )


@router.post("/data-manager/reported_activity/{uuid}/approve")
async def approve_reported_activity(
    uuid: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        if current_user.role != UserRole.DATA_MANAGER:
            raise HTTPException(
                status_code=403, detail="Access denied. User must be a data manager"
            )

        # Fetch the reported activity
        query = select(ReportActivity).where(ReportActivity.uuid == uuid)
        result = await db.execute(query)
        activity = result.scalar_one_or_none()

        if not activity:
            raise HTTPException(status_code=404, detail="Reported activity not found")

        # Check if the activity belongs to the user's organization
        report_query = select(Report).where(Report.uuid == activity.report_uuid)
        report_result = await db.execute(report_query)
        report = report_result.scalar_one_or_none()

        if not report or report.organization_uuid != current_user.organization_uuid:
            raise HTTPException(
                status_code=403,
                detail="Access denied. Activity does not belong to your organization",
            )

        # Check if the activity is in PENDING status
        if activity.status != ReportActivityStatus.PENDING:
            raise HTTPException(
                status_code=400, detail="Only pending activities can be approved"
            )

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
            },
        }

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        await db.rollback()
        print(f"Error: {e}")
        raise HTTPException(
            status_code=500, detail=f"An internal server error occurred: {str(e)}"
        )


@router.get("/data-manager/reports", response_model=PaginatedReportResponse)
async def get_reports(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Number of items per page"),
):
    try:
        if current_user.role != UserRole.DATA_MANAGER:
            raise HTTPException(
                status_code=403, detail="Access denied. User must be a data manager"
            )

        query = (
            select(
                Report,
                Project.name.label("project_name"),
                Organization.name.label("organization_name"),
            )
            .join(Project, Report.project_uuid == Project.uuid)
            .join(Organization, Report.organization_uuid == Organization.uuid)
            .where(Report.organization_uuid == current_user.organization_uuid)
            .order_by(Report.created_at.desc())
        )

        count_query = select(func.count()).select_from(query.subquery())
        total_items = await db.execute(count_query)
        total_items = total_items.scalar()
        total_pages = ceil(total_items / page_size)

        if page > total_pages and total_pages > 0:
            raise HTTPException(
                status_code=404,
                detail=f"Page {page} does not exist. Total pages: {total_pages}",
            )

        result = await db.execute(query.offset((page - 1) * page_size).limit(page_size))
        reports_data = result.all()

        reports_list = [
            ReportResponse(
                uuid=report.uuid,
                mou_application_uuid=report.mou_application_uuid,
                reported_by=report.reported_by,
                organization_uuid=report.organization_uuid,
                organization_name=organization_name,
                reported_at=report.reported_at,
                project_uuid=report.project_uuid,
                project_name=project_name,
                status=report.status,
            )
            for report, project_name, organization_name in reports_data
        ]

        return PaginatedReportResponse(
            items=reports_list,
            total_items=total_items,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(
            status_code=500, detail=f"An internal server error occurred: {str(e)}"
        )


@router.get("/reports", response_model=PaginatedReportResponse)
async def get_submitted_reports(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Number of items per page"),
):
    try:
        if current_user.role != UserRole.M_AND_E:
            raise HTTPException(
                status_code=403, detail="Access denied. User must be m and e"
            )

        query = (
            select(
                Report,
                Project.name.label("project_name"),
                Organization.name.label("organization_name"),
            )
            .join(Project, Report.project_uuid == Project.uuid)
            .join(Organization, Report.organization_uuid == Organization.uuid)
            .where(Report.status == ReportStatus.REPORTED)
            .order_by(Report.reported_at.desc())
        )

        count_query = select(func.count()).select_from(query.subquery())
        total_items = await db.execute(count_query)
        total_items = total_items.scalar()
        total_pages = ceil(total_items / page_size)

        if page > total_pages and total_pages > 0:
            raise HTTPException(
                status_code=404,
                detail=f"Page {page} does not exist. Total pages: {total_pages}",
            )

        result = await db.execute(query.offset((page - 1) * page_size).limit(page_size))
        reports_data = result.all()

        reports_list = [
            {
                "uuid": str(report.uuid),
                "mou_application_uuid": str(report.mou_application_uuid),
                "reported_by": report.reported_by,
                "organization_uuid": str(report.organization_uuid),
                "organization_name": organization_name,
                "reported_at": (
                    report.reported_at.isoformat() if report.reported_at else None
                ),
                "project_uuid": str(report.project_uuid),
                "project_name": project_name,
                "status": report.status.value,
            }
            for report, project_name, organization_name in reports_data
        ]

        return PaginatedReportResponse(
            items=reports_list,
            total_items=total_items,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(
            status_code=500, detail=f"An internal server error occurred: {str(e)}"
        )


@router.get(
    "/data-manager/report/{uuid}/activities",
    response_model=PaginatedReportedActivityResponse,
)
async def get_report_activities(
    uuid: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Number of items per page"),
):
    try:
        if current_user.role not in [UserRole.DATA_MANAGER, UserRole.M_AND_E]:
            raise HTTPException(
                status_code=403,
                detail="Access denied. User must be a data manager or m and e",
            )

        service = ReportActivityService(db)

        activities_data, total_items = await service.get_paginated_activities(
            uuid, page, page_size
        )

        total_pages = ceil(total_items / page_size)
        if page > total_pages > 0:
            raise HTTPException(
                status_code=404,
                detail=f"Page {page} does not exist. Total pages: {total_pages}",
            )

        grouped_activities = {}
        for report_activity, project, activity in activities_data:
            print("\nACTIVITY: ", activity)
            print("\nREPORT ACTIVITY: ", report_activity)
            activity_dict = ReportedActivityResponse(
                # Fields from Activity
                uuid=str(activity.uuid),
                name=activity.name,
                description=activity.description,
                start_date=activity.start_date,
                end_date=activity.end_date,
                implementer=activity.implementer,
                implementer_unit=activity.implementer_unit,
                fiscal_year=activity.fiscal_year,
                project_name=project.name,
                planned_budget=(
                    sum(detail.budget for detail in activity.input_details)
                    if activity.input_details
                    else None
                ),
                currency=project.currency,
                status=activity.status,
                report_status=activity.report_status,
                input_details=[
                    {
                        "uuid": str(detail.uuid),
                        "category": detail.input_category.name,
                        "input": detail.input.name,
                        "budget": detail.budget,
                        "district": detail.district,
                        "province": detail.province,
                    }
                    for detail in activity.input_details
                ],
                domains=[
                    {
                        "uuid": str(domain.uuid),
                        "domain_intervention": domain.domain_intervention.name,
                        "sub_domain": domain.sub_domain.name,
                        "sub_domain_function": domain.sub_domain_function.name,
                        "sub_function": domain.sub_function.name,
                    }
                    for domain in activity.domains
                ],
                # Fields from ReportActivity
                report_uuid=str(report_activity.report_uuid),
                reported_by=report_activity.reported_by,
                executed_budget=report_activity.executed_budget,
                actual_start_date=(
                    report_activity.actual_start_date.date()
                    if report_activity.actual_start_date
                    else None
                ),
                actual_end_date=(
                    report_activity.actual_end_date.date()
                    if report_activity.actual_end_date
                    else None
                ),
                report_activity_status=report_activity.status,
                report_activity_uuid=str(report_activity.uuid),
                accomplishments=report_activity.accomplishments,
                comments=[
                    {
                        "uuid": str(comment.uuid),
                        "content": comment.content,
                        "created_at": comment.created_at,
                    }
                    for comment in report_activity.comments
                ],
            )

            if project.uuid not in grouped_activities:
                grouped_activities[project.uuid] = ReportedActivityProjectResponse(
                    project_name=project.name,
                    project_uuid=str(project.uuid),
                    project_currency=project.currency,
                    activities=[],
                )

            grouped_activities[project.uuid].activities.append(activity_dict)

        items = list(grouped_activities.values())

        return PaginatedReportedActivityResponse(
            items=items,
            total_items=total_items,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"An internal server error occured: {str(e)}"
        )


@router.patch("/data-manager/report/{uuid}/submit")
async def submit_report(
    uuid: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        if current_user.role != UserRole.DATA_MANAGER:
            raise HTTPException(
                status_code=403, detail="Access denied. User must be a data manager"
            )

        # Fetch the report with related data
        query = (
            select(Report)
            .options(
                selectinload(Report.mou_application),
                selectinload(Report.project),
                selectinload(Report.reported_activities),
            )
            .where(
                Report.uuid == uuid,
                Report.organization_uuid == current_user.organization_uuid,
            )
        )
        result = await db.execute(query)
        report = result.scalar_one_or_none()

        if not report:
            raise HTTPException(
                status_code=404, detail="Report not found or access denied"
            )

        if report.status != ReportStatus.PENDING:
            raise HTTPException(
                status_code=400, detail="Only pending reports can be submitted"
            )

        # Update the report status
        report.status = ReportStatus.REPORTED
        report.reported_by = current_user.first_name + " " + current_user.last_name
        report.reported_at = datetime.utcnow()

        # Generate implementation plan
        implementation_plan_path, implementation_plan_filename = (
            await generate_implementation_plan(report, db)
        )

        report_organization_uuid = report.organization_uuid

        organization_query = select(Organization).where(
            Organization.uuid == report_organization_uuid
        )
        organization_result = await db.execute(organization_query)
        organization = organization_result.scalar_one_or_none()

        report_mou_application_uuid = report.mou_application_uuid

        mou_application_query = select(MouApplication).where(
            MouApplication.uuid == report_mou_application_uuid
        )
        mou_application_result = await db.execute(mou_application_query)
        report_mou_application = mou_application_result.scalar_one_or_none()

        report_mou_detail_uuid = report_mou_application.mou_detail_id

        mou_detail_query = select(MouDetail).where(
            MouDetail.uuid == report_mou_detail_uuid
        )
        mou_detail_result = await db.execute(mou_detail_query)
        report_mou_detail = mou_detail_result.scalar_one_or_none()

        # Create a new Document for the implementation plan
        implementation_plan_document = Document(
            name=f"Implementation Plan - {report.project.name}",
            description="Implementation Plan Report",
            document_type=DocumentType.ADDITIONAL_DOCUMENT,
            path=implementation_plan_path,
            filename=implementation_plan_filename,
            report=report,
            created_by=current_user.email,
            organization=organization,
            mou_detail=report_mou_detail,
        )

        db.add(implementation_plan_document)
        db.add(report)
        await db.commit()
        await db.refresh(report)
        await db.refresh(implementation_plan_document)

        return {
            "message": "Report submitted successfully",
            "report": {
                "uuid": str(report.uuid),
                "status": report.status.value,
                "reported_by": report.reported_by,
                "reported_at": report.reported_at.isoformat(),
                "project_uuid": str(report.project_uuid),
                "implementation_plan": {
                    "uuid": str(implementation_plan_document.uuid),
                    "name": implementation_plan_document.name,
                    "filename": implementation_plan_document.filename,
                    "path": implementation_plan_document.path,  # Added the document path here
                },
            },
        }

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        await db.rollback()
        print(f"Error: {e}")
        raise HTTPException(
            status_code=500, detail=f"An internal server error occurred: {str(e)}"
        )
