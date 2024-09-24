from typing import List, Dict, Union, Any

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlmodel.ext.asyncio.session import AsyncSession
from uuid import UUID

from db.models import Project, Activity, InputDetail, ActivityDomain, ReportActivity
from schemas.activity import ActivityList, ActivityDomainDetail
from schemas.input_detail import InputDetailRead


def convert_activity_to_schema(activity: Activity) -> ActivityList:
    return ActivityList(
        uuid=activity.uuid,
        project_id=activity.project_id,
        name=activity.name,
        implementer=activity.implementer,
        implementer_unit=activity.implementer_unit,
        fiscal_year=activity.fiscal_year,
        status=activity.status,
        reporting_status=activity.report_status,
        input_details=[
            InputDetailRead(
                uuid=input_detail.uuid,
                input_category=input_detail.input_category,
                input=input_detail.input,
                province=input_detail.province,
                district=input_detail.district,
                budget=input_detail.budget,
                created_at=input_detail.created_at,
                created_by=input_detail.created_by
            ) for input_detail in activity.input_details
        ],
        start_date=activity.start_date,
        end_date=activity.end_date,
        domains=[
            ActivityDomainDetail(
                uuid=domain.uuid,
                domain_intervention=domain.domain_intervention,
                sub_domain=domain.sub_domain,
                sub_domain_function=domain.sub_domain_function,
                sub_function=domain.sub_function
            ) for domain in activity.domains
        ]
    )


def convert_activities_to_schema(activities: List[Activity]) -> List[ActivityList]:
    return [convert_activity_to_schema(activity) for activity in activities]


async def fetch_activities_for_project(db: AsyncSession, project_id: UUID) -> List[ActivityList]:
    query = (
        select(Activity)
        .where(Activity.project_id == project_id)
        .options(
            selectinload(Activity.input_details).selectinload(InputDetail.input_category),
            selectinload(Activity.input_details).selectinload(InputDetail.input),
            selectinload(Activity.domains).selectinload(ActivityDomain.domain_intervention),
            selectinload(Activity.domains).selectinload(ActivityDomain.sub_domain),
            selectinload(Activity.domains).selectinload(ActivityDomain.sub_domain_function),
            selectinload(Activity.domains).selectinload(ActivityDomain.sub_function),
        )
    )
    result = await db.execute(query)
    activities = result.scalars().all()
    return [convert_activity_to_schema(activity) for activity in activities]


async def fetch_activities_for_projects(db: AsyncSession, projects: List[Project]) -> Dict[UUID, List[ActivityList]]:
    activities_by_project = {}
    for project in projects:
        activities = await fetch_activities_for_project(db, project.uuid)
        activities_by_project[project.uuid] = activities
    return activities_by_project
