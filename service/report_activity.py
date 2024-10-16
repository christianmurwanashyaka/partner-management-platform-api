import uuid
from typing import List

from fastapi import HTTPException
from sqlalchemy import select, and_, or_, distinct, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from db.models import User, Report, UserRole, ReportActivity, Activity, Project, InputDetail, ActivityDomain


class ReportActivityService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def validate_report_access(self, report_uuid: uuid.UUID, user: User) -> Report:
        query = (
            select(Report)
            .where(Report.uuid == report_uuid)
            .where(or_(
                and_(Report.organization_uuid == user.organization_uuid,
                     user.role == UserRole.DATA_MANAGER),
                user.role == UserRole.M_AND_E
            ))
        )
        result = await self.db.execute(query)
        report = result.scalar_one_or_none()

        if not report:
            raise HTTPException(
                status_code=404,
                detail='Report not found or access denied'
            )
        return report

    async def get_paginated_activities(
            self,
            report_uuid: uuid.UUID,
            page: int,
            page_size: int
    ) -> tuple[List[tuple], int]:
        # Base query for activities
        query = (
            select(ReportActivity, Project, Activity)
            .distinct(Activity.uuid)
            .join(Report, ReportActivity.report_uuid == Report.uuid)
            .join(Project, Report.project_uuid == Project.uuid)
            .join(
                Activity,
                and_(
                    Activity.project_id == Project.uuid,
                    Activity.report_uuid == Report.uuid
                )
            )
            .where(ReportActivity.report_uuid == report_uuid)
            .options(
                selectinload(ReportActivity.comments),
                selectinload(Activity.input_details).joinedload(InputDetail.input_category),
                selectinload(Activity.input_details).joinedload(InputDetail.input),
                selectinload(Activity.domains).joinedload(ActivityDomain.domain_intervention),
                selectinload(Activity.domains).joinedload(ActivityDomain.sub_domain),
                selectinload(Activity.domains).joinedload(ActivityDomain.sub_domain_function),
                selectinload(Activity.domains).joinedload(ActivityDomain.sub_function),
            )
            .order_by(Activity.uuid, ReportActivity.created_at.desc())
        )

        # Count query for pagination
        count_query = (
            select(func.count(distinct(Activity.uuid)))
            .join(Report, Activity.report_uuid == Report.uuid)
            .where(Report.uuid == report_uuid)
        )

        total_count = await self.db.execute(count_query)
        total_items = total_count.scalar()

        # Apply pagination
        results = await self.db.execute(
            query.offset((page - 1) * page_size).limit(page_size)
        )

        return results.all(), total_items