import uuid
from fastapi import APIRouter, Request, Depends, HTTPException, status, Query
from sqlalchemy import func, delete
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload, joinedload
from sqlmodel.ext.asyncio.session import AsyncSession

from api.dependencies.access_control import partner_access
from api.dependencies.auth import get_current_user
from api.dependencies.email_notification_handler import get_email_notification_handler
from api.endpoints.mou_application import update_related_mou_application
from db.database import get_db
from db.models import Activity, MouDetail, MouApplication, MouApplicationStatus
from db.models.organization import Organization
from db.models.pagination import PaginatedResponse
from db.models.project import Project, Goal
from db.models.user import User, UserRole
from helpers.db import get_all_items, get_items_by_criteria
from notification.handlers import EmailNotificationHandler
from schemas.activity import ActivityList
from schemas.project import ProjectRead, ProjectCreate, ProjectUpdate, ProjectList

router = APIRouter()


@router.post('/', response_model=ProjectRead, dependencies=[Depends(partner_access)])
async def create_project(request: Request, project: ProjectCreate, db: AsyncSession = Depends(get_db)):
    user = request.state.user.email
    if project.funding_source_id is None and project.other_funding_source is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either funding_source_id or other_funding_source must be provided"
        )

    calculated_total_budget = sum(item.budget for item in project.fiscal_year_budgets)

    if project.total_budget is not None and abs(project.total_budget - calculated_total_budget) > 0.01:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provided total budget does not match the sum of fiscal year budgets"
        )

    total_budget = project.total_budget if project.total_budget is not None else calculated_total_budget

    new_project = Project(
        name=project.name,
        description=project.description,
        budget_type_id=project.budget_type_id,
        fiscal_year_budgets=[{"fiscal_year": item.fiscal_year, "budget": item.budget} for item in project.fiscal_year_budgets],
        total_budget=total_budget,
        currency=project.currency,
        overall_goal=project.overall_goal,
        organization_id=project.organization_id,
        funding_unit_id=project.funding_unit_id,
        funding_source_id=project.funding_source_id,
        other_funding_source=project.other_funding_source,
        duration=project.duration,
        created_by=user
    )
    db.add(new_project)

    for goal_data in project.goals:
        new_goal = Goal(
            name=goal_data.name,
            description=goal_data.description,
            project_id=new_project.uuid,
            created_by=user
        )
        db.add(new_goal)

    try:
        await db.commit()
        await db.refresh(new_project)
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    return new_project


@router.patch('/{uuid}', response_model=ProjectRead, dependencies=[Depends(partner_access)])
async def update_project(
        uuid: uuid.UUID,
        project_update: ProjectUpdate,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user),
        email_handler: EmailNotificationHandler = Depends(get_email_notification_handler)
):
    try:
        # Fetch the existing project with eager loading for goals
        query = select(Project).options(
            joinedload(Project.goals)
        ).where(Project.uuid == uuid)

        result = await db.execute(query)
        project = result.scalars().unique().first()

        if not project:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Project not found')

        if project.created_by != current_user.email and current_user.role != UserRole.ADMIN:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Not authorized to update this project')

        # Update the project fields
        update_data = project_update.dict(exclude_unset=True)

        if 'fiscal_year_budgets' in update_data:
            project.fiscal_year_budgets = update_data['fiscal_year_budgets']
            calculated_total = sum(fby['budget'] for fby in update_data['fiscal_year_budgets'])

            if 'total_budget' in update_data:
                if abs(update_data['total_budget'] - calculated_total) > 0.01:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                        detail="Provided total budget does not match the sum of fiscal year budgets")
            else:
                project.total_budget = calculated_total
        elif 'total_budget' in update_data:
            project.total_budget = update_data['total_budget']

        for key, value in update_data.items():
            if key not in ['fiscal_year_budgets', 'total_budget', 'goals']:
                setattr(project, key, value)

        # Update goals
        if 'goals' in update_data:
            # Delete existing goals
            await db.execute(delete(Goal).where(Goal.project_id == project.uuid))
            # Add new goals
            new_goals = [
                Goal(
                    project_id=project.uuid,
                    name=goal['name'],
                    description=goal['description'],
                    created_by=current_user.email
                )
                for goal in update_data['goals']
            ]
            db.add_all(new_goals)

        await db.commit()
        await db.refresh(project)

        await update_related_mou_application(project, db, email_handler)

        return project
    except ValueError as ve:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get('/', response_model=PaginatedResponse[ProjectList])
async def get_projects(
    page: int = 1,
    page_size: int = 100,
    approved: bool = Query(False, description="Filter projects with approved MOU applications only"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        if current_user.role not in ['admin', 'moh_staff', 'partner']:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail='You are not authorized to perform this action')

        query = select(Project.uuid, Project.name, Project.duration, Project.currency, Project.fiscal_year_budgets, Project.total_budget)

        if current_user.role == 'partner':
            query = query.join(Organization).filter(Organization.created_by == current_user.email)

        if approved:
            query = query.join(MouDetail, MouDetail.project_id == Project.uuid)
            query = query.join(MouApplication, MouApplication.mou_detail_id == MouDetail.uuid)
            query = query.filter(MouApplication.status == MouApplicationStatus.APPROVED)

        total_items = await db.scalar(select(func.count()).select_from(query.subquery()))

        projects = await db.execute(query.offset((page - 1) * page_size).limit(page_size))

        projects = [ProjectList(
            uuid=p.uuid,
            name=p.name,
            duration=p.duration,
            currency=p.currency,
            fiscal_year_budgets=p.fiscal_year_budgets,
            total_budget=p.total_budget,
        ) for p in projects.fetchall()]

        total_pages = (total_items + page_size - 1) // page_size

        return PaginatedResponse(
            page=page,
            page_size=page_size,
            total_items=total_items,
            total_pages=total_pages,
            data=projects
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# TODO: SHOULD VALIDATE THAT PROJECT EXISTS FIRST
@router.get('/{uuid}/activities/', response_model=PaginatedResponse[ActivityList])
async def get_project_activities(
        uuid: uuid.UUID,
        page: int = 1,
        page_size: int = 100,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    query = (select(Activity)
             .where(Activity.project_id == uuid)
             .order_by(Activity.created_at.desc())
             .offset((page - 1) * page_size)
             .limit(page_size))

    query = query.options(selectinload(Activity.input_details))
    activities = await db.execute(query)
    activities_list = activities.scalars().all()

    if not activities_list:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No activities found for this project")

    total_items_query = select(func.count()).select_from(Activity).where(Activity.project_id == uuid)
    total_items = (await db.execute(total_items_query)).scalar_one()
    total_pages = (total_items + page_size - 1) // page_size

    return PaginatedResponse(
        page=page,
        page_size=page_size,
        total_items=total_items,
        total_pages=total_pages,
        data=activities_list
    )


@router.get('/{uuid}', response_model=ProjectRead)
async def get_project(
        uuid: str,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    try:
        query = select(Project).filter(Project.uuid == uuid).options(
            joinedload(Project.organization),
            joinedload(Project.activities)  # Add any other related models as needed
        )

        project_result = await db.execute(query)
        project = project_result.unique().scalar_one_or_none()

        if not project:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail='Project not found')

        # Access control based on user role
        if current_user.role in ['admin', 'moh_staff']:
            return project
        elif current_user.role == 'partner' and project.organization.created_by == current_user.email:
            return project
        else:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail='You are not authorized to access this project')

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
