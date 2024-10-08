from datetime import datetime
from math import ceil

from uuid import UUID

import uuid
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import select, func
from sqlalchemy.orm import joinedload, selectinload
from sqlmodel.ext.asyncio.session import AsyncSession

from api.dependencies.auth import get_current_user
from db.database import get_db
from db.models import User, UserRole, Activity, Report, ReportStatus, ReportActivity, MouDetail, MouApplication, \
    Organization, Project, InputDetail, ActivityDomain, MouApplicationStatus, Comment, ReportActivityStatus
from db.models.activity import ActivityStatus, ActivityReportingStatus
from schemas.report import ActivityResponse, ProjectActivitiesResponse, ReportActivityDetailResponse, CommentResponse, \
    ReportedActivityResponse
from schemas.report_activity import ReportActivityCreate, OrganizationProjectsResponse, \
    PaginatedOrganizationProjectsResponse, RequestChange, ReportActivityUpdateResponse, ReportActivityUpdateRequest

router = APIRouter()


@router.post('/data-reporter/activity', response_model=dict)
async def report_activity(
        report_activity_data: ReportActivityCreate,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    if current_user.role != UserRole.DATA_REPORTER:
        raise HTTPException(status_code=403, detail="Access denied. User must be a data reporter.")
    try:
        activity_query = select(Activity).options(joinedload(Activity.project)).where(
            (Activity.uuid == report_activity_data.activity_uuid) &
            (Activity.report_status == ActivityReportingStatus.READY_FOR_REPORT)
        )
        result = await db.execute(activity_query)
        activity = result.scalar_one_or_none()

        if not activity:
            raise HTTPException(status_code=404, detail="Activity not found or not ready for report")
        if activity.project.organization_id != current_user.organization_uuid:
            raise HTTPException(status_code=403, detail="Access denied. User must be in the same organization as the activity.")

        # Check if a report for this project already exists, if not create one
        report_query = select(Report).where(
            (Report.project_uuid == activity.project_id) &
            (Report.status == ReportStatus.PENDING)
        )
        result = await db.execute(report_query)
        report = result.scalar_one_or_none()

        project = activity.project

        mou_detail_query = select(MouDetail).where(MouDetail.project_id == project.uuid)
        result = await db.execute(mou_detail_query)
        mou_detail = result.scalars().all()[0]

        mou_application_query = select(MouApplication).where(MouApplication.mou_detail_id == mou_detail.uuid)
        result = await db.execute(mou_application_query)
        mou_application = result.scalars().all()[0]

        mou_application_uuid = mou_application.uuid

        if not report:
            report = Report(
                project_uuid=activity.project_id,
                mou_application_uuid=mou_application_uuid,
                organization_uuid=current_user.organization_uuid,
                created_by=current_user.email,
                status=ReportStatus.PENDING
            )
            db.add(report)
            await db.commit()
            await db.refresh(report)

        # Create the ReportActivity
        new_report_activity = ReportActivity(
            report_uuid=report.uuid,
            executed_budget=report_activity_data.executed_budget,
            actual_start_date=report_activity_data.actual_start_date.replace(tzinfo=None),
            actual_end_date=report_activity_data.actual_end_date.replace(tzinfo=None),
            created_by=current_user.email,
            reported_by=current_user.first_name + ' ' + current_user.last_name,
            accomplishments=report_activity_data.accomplishments,
            activity_uuid=report_activity_data.activity_uuid,
        )

        db.add(new_report_activity)
        await db.commit()
        await db.refresh(new_report_activity)

        if report_activity_data.comment:
            new_comment = Comment(
                content=report_activity_data.comment,
                user_uuid=current_user.uuid,
                report_uuid=report.uuid,
                report_activity_uuid=new_report_activity.uuid,
                created_by=current_user.email
            )

            db.add(new_comment)
            await db.commit()
            await db.refresh(new_comment)

        # Update the Activity status
        activity.status = report_activity_data.status
        activity.report_status = ActivityReportingStatus.REPORTED
        activity.report_uuid = report.uuid

        await db.commit()
        return {
            "message": "Activity reported successfully",
            "report_activity_id": str(new_report_activity.uuid),
            "report_id": str(report.uuid)
        }
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"An internal server error occurred: {str(e)}")


@router.get('/m-and-e/activities', response_model=PaginatedOrganizationProjectsResponse)
async def get_activities_from_approved_applications(
        page: int = Query(1, ge=1, description='Page number'),
        page_size: int = Query(10, ge=1, le=100, description='Number of items per page'),
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    try:
        if current_user.role != UserRole.M_AND_E:
            raise HTTPException(status_code=403, detail='You are not authorized to do this action')
        # Query to get total count of activities
        count_query = select(func.count(Activity.uuid)).join(
            Project, Activity.project_id == Project.uuid
        ).join(
            MouDetail, Project.uuid == MouDetail.project_id
        ).join(
            MouApplication, MouDetail.uuid == MouApplication.mou_detail_id
        ).where(
            MouApplication.status == MouApplicationStatus.APPROVED
        )

        total_items = await db.execute(count_query)
        total_items = total_items.scalar()
        total_pages = ceil(total_items / page_size)

        if page > total_pages and total_pages > 0:
            raise HTTPException(status_code=404, detail=f"Page {page} does not exist. Total pages: {total_pages}")

        # Query to get paginated activities with related data
        query = (
            select(Activity, Project, Organization)
            .join(Project, Activity.project_id == Project.uuid)
            .join(Organization, Project.organization_id == Organization.uuid)
            .join(MouDetail, Project.uuid == MouDetail.project_id)
            .join(MouApplication, MouDetail.uuid == MouApplication.mou_detail_id)
            .options(
                selectinload(Activity.input_details).selectinload(InputDetail.input_category),
                selectinload(Activity.input_details).selectinload(InputDetail.input),
                selectinload(Activity.domains).selectinload(ActivityDomain.domain_intervention),
                selectinload(Activity.domains).selectinload(ActivityDomain.sub_domain),
                selectinload(Activity.domains).selectinload(ActivityDomain.sub_domain_function),
                selectinload(Activity.domains).selectinload(ActivityDomain.sub_function),
            )
            .where(MouApplication.status == MouApplicationStatus.APPROVED)
            .order_by(Organization.name, Project.name, Activity.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

        result = await db.execute(query)
        activities_data = result.all()

        # Group activities by organization and project
        grouped_data = {}
        for activity, project, organization in activities_data:
            org_uuid = str(organization.uuid)
            proj_uuid = str(project.uuid)

            if org_uuid not in grouped_data:
                grouped_data[org_uuid] = {
                    'organization_name': organization.name,
                    'organization_uuid': org_uuid,
                    'projects': {}
                }

            if proj_uuid not in grouped_data[org_uuid]['projects']:
                grouped_data[org_uuid]['projects'][proj_uuid] = {
                    'project_name': project.name,
                    'project_uuid': proj_uuid,
                    'project_currency': project.currency,
                    'activities': []
                }

            activity_dict = activity.__dict__
            activity_dict['uuid'] = str(activity_dict['uuid'])
            grouped_data[org_uuid]['projects'][proj_uuid]['activities'].append(
                ActivityResponse(**{**activity_dict, 'currency': project.currency})
            )

        # Structure the response
        items = [
            OrganizationProjectsResponse(
                organization_name=org_data['organization_name'],
                organization_uuid=org_data['organization_uuid'],
                projects=[
                    ProjectActivitiesResponse(**proj_data)
                    for proj_data in org_data['projects'].values()
                ]
            )
            for org_data in grouped_data.values()
        ]

        return PaginatedOrganizationProjectsResponse(
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


@router.get('/{uuid}', response_model=ReportActivityDetailResponse)
async def get_report_activity_details(
        uuid: UUID,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    try:
        if current_user.role not in [UserRole.DATA_MANAGER, UserRole.M_AND_E, UserRole.DATA_REPORTER]:
            raise HTTPException(status_code=403, detail='Access denied. User must be a data manager, M&E officer or data reporter')

        query = (
            select(ReportActivity)
            .options(
                joinedload(ReportActivity.comments),
                joinedload(ReportActivity.report).joinedload(Report.project),
                joinedload(ReportActivity.report).joinedload(Report.organization)
            )
            .where(ReportActivity.uuid == uuid)
        )

        if current_user.role == UserRole.DATA_MANAGER:
            query = query.where(ReportActivity.report.has(Report.organization_uuid == current_user.organization_uuid))

        result = await db.execute(query)
        report_activity = result.unique().scalar_one_or_none()

        if not report_activity:
            raise HTTPException(status_code=404, detail="Report Activity not found")

        return ReportActivityDetailResponse(
            uuid=report_activity.uuid,
            report_uuid=report_activity.report_uuid,
            reported_by=report_activity.reported_by,
            executed_budget=report_activity.executed_budget,
            actual_start_date=report_activity.actual_start_date,
            actual_end_date=report_activity.actual_end_date,
            status=report_activity.status,
            accomplishments=report_activity.accomplishments,
            comments=[
                CommentResponse(
                    uuid=comment.uuid,
                    content=comment.content,
                    created_at=comment.created_at,
                    created_by=comment.created_by
                ) for comment in report_activity.comments
            ],
            report_status=report_activity.report.status,
            project_name=report_activity.report.project.name,
            organization_name=report_activity.report.organization.name
        )

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=f"An internal server error occurred: {str(e)}")

@router.post('/{uuid}/request_change')
async def request_change_on_reported_activity(
        uuid: uuid.UUID,
        comment: RequestChange,
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
        if comment:
            new_comment = Comment(
                content=comment,
                user_uuid=current_user.uuid,
                report_uuid=report.uuid,
                report_activity_uuid=uuid,
                created_by=current_user.email
            )

            db.add(new_comment)
            await db.commit()
            await db.refresh(new_comment)

        activity.status = ReportActivityStatus.NEEDS_CHANGE
        db.add(activity)
        await db.commit()
        await db.refresh(activity)

        return {
            "message": "Change requested successfully",
            "activity": {
                "uuid": str(activity.uuid),
                "status": activity.status.value,
                "report_uuid": str(activity.report_uuid),
            }
        }

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        await db.rollback()
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=f"An internal server error occurred: {str(e)}")


@router.patch('/{uui}', response_model=ReportActivityUpdateResponse)
async def update_report_activity(
        uuid: uuid.UUID,
        update_data: ReportActivityUpdateRequest,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    try:
        if current_user.role != UserRole.DATA_REPORTER:
            raise HTTPException(status_code=403, detail='Access denied. User must be a data reporter')

        # Fetch the report activity from the database
        result = await db.execute(select(ReportActivity).where(ReportActivity.uuid == uuid))
        report_activity = result.scalar_one_or_none()

        if not report_activity:
            raise HTTPException(status_code=404, detail="Report activity not found")

            # Check if the activity belongs to the user's organization
            report_query = select(Report).where(Report.uuid == activity.report_uuid)
            report_result = await db.execute(report_query)
            report = report_result.scalar_one_or_none()

            if not report or report.organization_uuid != current_user.organization_uuid:
                raise HTTPException(status_code=403,
                                    detail='Access denied. Activity does not belong to your organization')

        # Update only the provided fields
        if update_data.executed_budget is not None:
            report_activity.executed_budget = update_data.executed_budget
        if update_data.actual_start_date is not None:
            report_activity.actual_start_date = update_data.actual_start_date
        if update_data.actual_end_date is not None:
            report_activity.actual_end_date = update_data.actual_end_date
        if update_data.status is not None:
            report_activity.status = update_data.status
        if update_data.accomplishments is not None:
            report_activity.accomplishments = update_data.accomplishments
        if update_data.comment:
            new_comment = Comment(
                content=update_data,
                user_uuid=current_user.uuid,
                report_uuid=report.uuid,
                report_activity_uuid=uuid,
                created_by=current_user.email
            )

            db.add(new_comment)
            await db.commit()
            await db.refresh(new_comment)

        # Commit the changes
        report_activity.status = ReportActivityStatus.CHANGED
        await db.commit()
        await db.refresh(report_activity)

        return report_activity
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"An internal server error occurred: {str(e)}")