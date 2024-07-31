import uuid
from fastapi import APIRouter, Request, Depends, HTTPException, status
from sqlalchemy import delete, func
from sqlalchemy.orm import joinedload, aliased
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.future import select

from api.dependencies.access_control import admin_access
from api.dependencies.auth import get_current_user
from db.database import get_db
from db.models import SubDomain, DomainIntervention
from db.models.user import User, UserRole, MOHStaffLevel
from db.models.pagination import PaginatedResponse
from db.models.user_domain import UserDomain
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
