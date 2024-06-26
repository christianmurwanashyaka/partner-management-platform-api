import uuid
from fastapi import APIRouter, Request, Depends, HTTPException, status
from sqlalchemy import func, delete
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload, joinedload
from sqlmodel.ext.asyncio.session import AsyncSession

from api.dependencies.access_control import partner_access
from api.dependencies.auth import get_current_user
from api.endpoints.mou_application import update_related_mou_application
from db.database import get_db
from db.models import Activity
from db.models.organization import Organization
from db.models.pagination import PaginatedResponse
from db.models.project import Project, Goal
from db.models.user import User, UserRole
from helpers.db import get_all_items, get_items_by_criteria
from schemas.activity import ActivityList
from schemas.project import ProjectRead, ProjectCreate, ProjectUpdate

router = APIRouter()


@router.post('/', response_model=ProjectRead, dependencies=[Depends(partner_access)])
async def create_project(request: Request, project: ProjectCreate, db: AsyncSession = Depends(get_db)):
    user = request.state.user.email
    new_project = Project(
        name=project.name,
        description=project.description,
        budget_type_id=project.budget_type_id,
        budget=project.budget,
        currency=project.currency,
        overall_goal=project.overall_goal,
        organization_id=project.organization_id,
        funding_unit_id=project.funding_unit_id,
        funding_source_id=project.funding_source_id,
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
        current_user: User = Depends(get_current_user)
):
    try:
        # Fetch the existing project with eager loading for goals
        query = select(Project).options(
            joinedload(Project.goals)
        ).where(Project.uuid == uuid)

        result = await db.execute(query)
        project_list = result.scalars().unique().all()

        if not project_list:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail='Project not found')

        project = project_list[0]

        if project.created_by != current_user.email and current_user.role != UserRole.ADMIN:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail='Not authorized to update this project')

        # Update the project fields
        for key, value in project_update.dict(exclude_unset=True).items():
            if key != 'goals':
                setattr(project, key, value)

        # Update goals
        if project_update.goals is not None:
            # Delete existing goals
            await db.execute(delete(Goal).where(Goal.project_id == project.uuid))
            # Add new goals
            new_goals = [
                Goal(
                    project_id=project.uuid,
                    name=goal.name,
                    description=goal.description,
                    created_by=current_user.email
                )
                for goal in project_update.goals
            ]
            db.add_all(new_goals)

        await db.commit()
        await db.refresh(project)

        await update_related_mou_application(project, db)

        return project
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get('/', response_model=PaginatedResponse[ProjectRead])
async def get_projects(
        page: int = 1,
        page_size: int = 100,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    if current_user.role in ['admin', 'moh_staff']:
        paginated_response = await get_all_items(db, Project, page=page, page_size=page_size, include=['organization'])
    elif current_user.role == 'partner':
        query = select(Project).join(Organization).filter(Organization.created_by == current_user.email)
        total_items = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar_one()
        projects = await get_items_by_criteria(db, query.offset((page - 1) * page_size).limit(page_size))
        total_pages = (total_items + page_size - 1) // page_size
        paginated_response = PaginatedResponse(
            page=page,
            page_size=page_size,
            total_items=total_items,
            total_pages=total_pages,
            data=projects
        )
    else:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail='You are not authorized to perform this action')

    return paginated_response


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
