from datetime import datetime
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from sqlmodel.ext.asyncio.session import AsyncSession

from api.dependencies.auth import get_current_user
from db.database import get_db
from db.models import User, UserRole, Activity, Report, ReportStatus, ReportActivity
from db.models.activity import ActivityStatus
from schemas.report_activity import ReportActivityCreate

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
            (Activity.status == ActivityStatus.READY_FOR_REPORT)
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

        mou_detail = project.mou_details[0]  # Assuming there's only one mou_detail per project
        mou_application_uuid = mou_detail.mou_application.uuid

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
            created_by=current_user.email
        )
        db.add(new_report_activity)
        await db.commit()
        await db.refresh(new_report_activity)

        # Update the Activity status
        activity.status = ActivityStatus.REPORTED
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


