import uuid
from typing import Optional

from fastapi import APIRouter, Request, Depends, HTTPException, status, Query
from sqlalchemy import delete, func, or_, distinct
from sqlalchemy.orm import joinedload, aliased
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.future import select

from api.dependencies.access_control import admin_access
from api.dependencies.auth import get_current_user
from db.database import get_db
from db.models import SubDomain, DomainIntervention, MouApplication, Organization, OrganizationType, Activity, \
    InputDetail, MouDetail, Project, ActivityDomain
from db.models.user import User, UserRole, MOHStaffLevel
from db.models.pagination import PaginatedResponse
from db.models.user_domain import UserDomain
from schemas.mou_application import MouApplicationOrganizationRead
from schemas.user import UserProfile, UserCreate, SignupResponse, UserUpdate, AssignDomain
from helpers.db import check_if_exists, get_all_items, get_first_item
from utils.security import get_password_hash

router = APIRouter()


@router.get('/', response_model=PaginatedResponse[UserProfile], dependencies=[Depends(admin_access)])
async def get_users(page: int = 1, page_size: int = 100, db: AsyncSession = Depends(get_db)):
    return await get_all_items(db, User, page=page, page_size=page_size)


@router.patch('/{uuid}', response_model=UserProfile)
async def update_user(
        uuid: uuid.UUID,
        user_update: UserUpdate,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    try:
        query = select(User).where(User.uuid == uuid)
        result = await db.execute(query)
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail='User not found')

        if user.email != current_user.email and current_user.role != UserRole.ADMIN:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail='Not authorized to update this user')

        update_data = user_update.dict(exclude_unset=True)

        if 'password' in update_data:
            update_data['password'] = get_password_hash(update_data['password'])

        for key, value in update_data.items():
            setattr(user, key, value)

        await db.commit()
        await db.refresh(user)

        return user
    except Exception as e:
        await db.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post('/domain')
async def assign_domain(
        assign_domain_data: AssignDomain,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    try:
        # Check if the current user is an admin
        if current_user.role != UserRole.ADMIN:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to assign domain")

        # Fetch the user to be assigned
        user_query = select(User).where(User.uuid == assign_domain_data.user_uuid)
        result = await db.execute(user_query)
        user = result.scalars().first()

        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        # Check if the user is MOH staff with technical department level
        if user.role != UserRole.MOH_STAFF or user.level != MOHStaffLevel.TECHNICAL_DEPARTMENT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only MOH staff with technical department level can be assigned domains"
            )

        # Fetch the domain to be assigned
        domain_query = select(DomainIntervention).where(DomainIntervention.uuid == assign_domain_data.domain_uuid)
        result = await db.execute(domain_query)
        domain = result.scalars().first()

        if not domain:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Domain not found")

        # Fetch all subdomains of the domain
        all_subdomains = await db.execute(select(SubDomain).where(SubDomain.domain_id == domain.uuid))
        all_subdomains = all_subdomains.scalars().all()

        # If subdomain_uuid_list is provided, validate and fetch those subdomains
        if assign_domain_data.subdomain_uuid_list:
            subdomains_query = select(SubDomain).where(SubDomain.uuid.in_(assign_domain_data.subdomain_uuid_list))
            result = await db.execute(subdomains_query)
            subdomains = result.scalars().all()

            # Check if all provided subdomain UUIDs are valid
            invalid_subdomains = set(assign_domain_data.subdomain_uuid_list) - {subdomain.uuid for subdomain in subdomains}
            if invalid_subdomains:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid subdomain IDs: {', '.join(map(str, invalid_subdomains))}"
                )

            # Check if all subdomains belong to the specified domain
            if any(subdomain.domain_id != domain.uuid for subdomain in subdomains):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="One or more subdomains do not belong to the specified domain"
                )
        else:
            subdomains = all_subdomains

        await db.execute(delete(UserDomain).where(UserDomain.user_id == user.uuid))

        # Create a single UserDomain entry
        user_domain = UserDomain(
            user_id=user.uuid,
            domain_id=domain.uuid,
            created_by=current_user.email
        )

        # If specific subdomains are provided, assign them
        if assign_domain_data.subdomain_uuid_list:
            user_domain.subdomain_ids = assign_domain_data.subdomain_uuid_list
        else:
            # If no specific subdomains are provided, assign all subdomains of the domain
            user_domain.subdomain_ids = [subdomain.uuid for subdomain in all_subdomains]

        db.add(user_domain)

        await db.commit()
        await db.refresh(user)

        return {
            "message": "Domain and subdomains assigned successfully",
            "assigned_domain": domain.name,
            "assigned_subdomains": [subdomain.name for subdomain in subdomains]
        }

    except HTTPException as http_exc:
        # Re-raise HTTP exceptions as they are already properly formatted
        raise http_exc

    except Exception as e:
        # Rollback the transaction in case of an error
        await db.rollback()
        # Return a generic error message to the client
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred. Please try again later. {str(e)}"
        )


@router.get('/{uuid}/domain')
async def get_user_domain(
        uuid: uuid.UUID,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    try:
        if current_user.role != UserRole.ADMIN:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to get user domain")

        # Create aliases for the tables we'll be joining
        user_domain_alias = aliased(UserDomain)
        domain_alias = aliased(DomainIntervention)
        subdomain_alias = aliased(SubDomain)

        # Construct a single query that joins all necessary tables
        query = (
            select(User, user_domain_alias, domain_alias, subdomain_alias)
            .join(user_domain_alias, User.uuid == user_domain_alias.user_id)
            .join(domain_alias, user_domain_alias.domain_id == domain_alias.uuid)
            .join(subdomain_alias, subdomain_alias.uuid == func.any(user_domain_alias.subdomain_ids))
            .where(User.uuid == uuid)
        )

        result = await db.execute(query)
        rows = result.all()

        if not rows:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User or domain assignment not found")

        # Process the results
        user = rows[0][0]  # User object
        domain = rows[0][2]  # DomainIntervention object

        # Use a dictionary to ensure uniqueness of subdomains
        subdomains_dict = {str(row[3].uuid): row[3] for row in rows}
        subdomains = list(subdomains_dict.values())

        response = {
            "user": {
                "uuid": str(user.uuid),
                "email": user.email,
            },
            "domain": {
                "uuid": str(domain.uuid),
                "name": domain.name,
            },
            "sub_domains": [
                {"uuid": str(subdomain.uuid), "name": subdomain.name}
                for subdomain in subdomains
            ]
        }

        return response
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        print(f"Unexpected error: {str(e)}")  # For debugging
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred. Please try again later. {str(e)}"
        )


@router.get('/{uuid}/domain/applications', response_model=PaginatedResponse[MouApplicationOrganizationRead])
async def get_user_domain_applications(
        uuid: uuid.UUID,
        page: int = 1,
        page_size: int = 100,
        sort_by: Optional[str] = Query(None, description="Field to sort by: status, budget, created_at"),
        order: Optional[str] = Query("desc", description="Sort order: asc or desc"),
        search: Optional[str] = Query(None, description="Search query for names"),
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    try:
        # Authorization check
        if current_user.role != UserRole.ADMIN and current_user.uuid != uuid:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view these applications")

        # Fetch the user's assigned domains
        user_domains_query = select(UserDomain).where(UserDomain.user_id == uuid)
        user_domains_result = await db.execute(user_domains_query)
        user_domains = user_domains_result.scalars().all()

        if not user_domains:
            return PaginatedResponse(page=page, page_size=page_size, total_items=0, total_pages=0, data=[])

        # Extract domain and subdomain IDs
        domain_ids = [ud.domain_id for ud in user_domains]
        subdomain_ids = [id for ud in user_domains for id in ud.subdomain_ids]

        # Determine if we need to calculate the budget
        calculate_budget = sort_by == 'budget'

        # Base query
        base_query = select(
            MouApplication.created_at,
            MouApplication.submitted_by,
            MouApplication.uuid,
            MouApplication.status,
            MouApplication.next_level,
            Organization.name.label('organization'),
            OrganizationType.name.label('organization_type')
        )

        # Add budget calculation only if needed
        if calculate_budget:
            budget_subquery = (
                select(
                    Activity.project_id,
                    func.sum(InputDetail.budget).label('total_budget')
                )
                .join(InputDetail.activity)
                .group_by(Activity.project_id)
                .subquery()
            )
            base_query = base_query.add_columns(
                func.coalesce(budget_subquery.c.total_budget, 0).label('total_budget')
            )

        # Join tables
        base_query = base_query.join(MouApplication.mou_detail).\
            join(MouDetail.project).\
            join(Project.organization).\
            join(Organization.organization_type).\
            join(Project.activities).\
            join(Activity.domains).\
            join(ActivityDomain.domain_intervention).\
            join(ActivityDomain.sub_domain)

        if calculate_budget:
            base_query = base_query.outerjoin(budget_subquery, Project.uuid == budget_subquery.c.project_id)

        # Apply filters for user's assigned domains and subdomains
        domain_filter = or_(
            ActivityDomain.domain_intervention_id.in_(domain_ids),
            ActivityDomain.sub_domain_id.in_(subdomain_ids)
        )
        base_query = base_query.filter(domain_filter)

        # Add search functionality
        if search:
            search_filter = or_(
                Organization.name.ilike(f"%{search}%"),
                Activity.name.ilike(f"%{search}%"),
                DomainIntervention.name.ilike(f"%{search}%"),
                SubDomain.name.ilike(f"%{search}%")
            )
            base_query = base_query.filter(search_filter)

        # Count total items
        count_query = select(func.count(distinct(MouApplication.uuid))).select_from(base_query.subquery())
        total_items = (await db.execute(count_query)).scalar_one()

        # Apply sorting
        if sort_by:
            if sort_by == 'status':
                order_by = MouApplication.status.desc() if order == 'desc' else MouApplication.status.asc()
            elif sort_by == 'budget' and calculate_budget:
                order_by = budget_subquery.c.total_budget.desc() if order == 'desc' else budget_subquery.c.total_budget.asc()
            elif sort_by == 'created_at':
                order_by = MouApplication.created_at.desc() if order == 'desc' else MouApplication.created_at.asc()
            else:
                order_by = MouApplication.created_at.desc()  # Default sorting
        else:
            order_by = MouApplication.created_at.desc()  # Default sorting

        base_query = base_query.order_by(order_by)

        # Apply distinct and pagination
        paginated_query = (
            base_query.distinct()
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

        mou_applications = (await db.execute(paginated_query)).all()

        response_data = [
            MouApplicationOrganizationRead(
                created_at=app.created_at,
                submitted_by=app.submitted_by,
                reference_number=f"{app.created_at:%Y%m%d}-{app.uuid.int % 1000000:06d}",
                uuid=app.uuid,
                status=app.status,
                organization=app.organization,
                organization_type=app.organization_type,
                next_level=app.next_level,
                total_budget=app.total_budget if calculate_budget else None
            )
            for app in mou_applications
        ]

        return PaginatedResponse(
            page=page,
            page_size=page_size,
            total_items=total_items,
            total_pages=(total_items + page_size - 1) // page_size,
            data=response_data
        )

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))