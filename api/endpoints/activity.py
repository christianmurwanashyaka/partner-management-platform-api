from typing import List

import uuid
from fastapi import APIRouter, Request, Depends, HTTPException, status
from sqlalchemy import func, delete
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload
from sqlmodel.ext.asyncio.session import AsyncSession
from api.dependencies.access_control import partner_access
from api.dependencies.auth import get_current_user
from db.database import get_db
from db.models import OperationalZone, ActivityDomain
from db.models.activity import Activity
from db.models.input_detail import InputDetail
from db.models.pagination import PaginatedResponse
from db.models.user import User, UserRole
from schemas.activity import ActivityRead, ActivityCreate, ActivityList, OperationalZoneRead, ActivityDomainDetail, \
    ActivityUpdate, OperationalZoneUpdate, ActivityDomainUpdate
from schemas.input_detail import InputDetailRead, InputDetailUpdate

router = APIRouter()


@router.post('/', response_model=ActivityRead, dependencies=[Depends(partner_access)])
async def create_activity(request: Request, activity: ActivityCreate, db: AsyncSession = Depends(get_db)):
    user = request.state.user.email
    new_activity = Activity(
        project_id=activity.project_id,
        name=activity.name,
        implementer=activity.implementer,
        implementer_unit=activity.implementer_unit,
        fiscal_year=activity.fiscal_year,
        start_date=activity.start_date,
        end_date=activity.end_date,
        created_by=user
    )
    db.add(new_activity)
    await db.commit()
    await db.refresh(new_activity)

    print(f"New activity created with UUID: {new_activity.uuid}")

    try:
        # Handle domains
        activity_domains = []
        for domain in activity.domains:
            new_activity_domain = ActivityDomain(
                activity_id=new_activity.uuid,
                domain_intervention_id=domain.domain_intervention_id,
                sub_domain_id=domain.sub_domain_id,
                created_by=user
            )
            print(f"Creating activity domain with UUID: {new_activity_domain.uuid}, activity_id: {new_activity_domain.activity_id}")
            activity_domains.append(new_activity_domain)
        db.add_all(activity_domains)

        # Handle operational zones
        operational_zones = []
        for zone_data in activity.operational_zones:
            new_zone = OperationalZone(
                activity_id=new_activity.uuid,
                province=zone_data.province,
                district=zone_data.district,
                created_by=user
            )
            print(f"Creating operational zone with UUID: {new_zone.uuid}, activity_id: {new_zone.activity_id}")
            operational_zones.append(new_zone)
        db.add_all(operational_zones)

        # Handle input details
        input_details = []
        for input_detail_data in activity.input_details:
            new_input_detail = InputDetail(
                activity_id=new_activity.uuid,
                input_category_id=input_detail_data.input_category_id,
                input_id=input_detail_data.input_id,
                budget=input_detail_data.budget,
                district=input_detail_data.district,
                province=input_detail_data.province,
                created_by=user
            )
            print(f"Creating input detail with UUID: {new_input_detail.uuid}, activity_id: {new_input_detail.activity_id}")
            input_details.append(new_input_detail)
        db.add_all(input_details)

        await db.commit()

        # Additional logging to verify related entities
        print(f"Activity domains added: {activity_domains}")
        print(f"Operational zones added: {operational_zones}")
        print(f"Input details added: {input_details}")

    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create related entities: {str(e)}"
        )

    return new_activity


@router.patch('/{uuid}', response_model=ActivityRead, dependencies=[Depends(partner_access)])
async def update_activity(
        uuid: uuid.UUID,
        activity_update: ActivityUpdate,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    try:
        query = select(Activity).where(Activity.uuid == uuid)
        result = await db.execute(query)
        activity = result.scalar_one_or_none()

        if not activity:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail='Activity not found')

        if activity.created_by != current_user.email and current_user.role != UserRole.ADMIN:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail='You are not authorized to perform this action')

        for key, value in activity_update.dict(exclude_unset=True).items():
            setattr(activity, key, value)

        await db.commit()
        await db.refresh(activity)

        return activity

    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update activity: {str(e)}"
        )


@router.get('/', response_model=PaginatedResponse[ActivityList])
async def get_activities(
        page: int = 1,
        page_size: int = 100,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    if current_user.role in ['admin', 'swapteam_member']:
        query = select(Activity).order_by(Activity.created_at.desc())
        total_items = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar_one()
        activities = (await db.execute(query.offset((page - 1) * page_size).limit(page_size))).scalars().all()
    elif current_user.role == 'partner':
        query = select(Activity).filter(Activity.created_by == current_user.email).order_by(Activity.created_at.desc())
        total_items = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar_one()
        activities = (await db.execute(query.offset((page - 1) * page_size).limit(page_size))).scalars().all()
    else:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail='You are not authorized to perform this action')

    total_pages = (total_items + page_size - 1) // page_size
    paginated_response = PaginatedResponse(
        page=page,
        page_size=page_size,
        total_items=total_items,
        total_pages=total_pages,
        data=activities
    )

    return paginated_response


@router.patch('/{uuid}/operational_zones', response_model=ActivityRead, dependencies=[Depends(partner_access)])
async def update_activity_operational_zones(
        uuid: uuid.UUID,
        operational_zones: List[OperationalZoneUpdate],
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    try:
        query = select(Activity).where(Activity.uuid == uuid)
        result = await db.execute(query)
        activity = result.scalar_one_or_none()

        if not activity:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail='Activity not found')

        if activity.created_by != current_user.email and current_user.role != UserRole.ADMIN:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail='You are not authorized to perform this action')

        await db.execute(delete(OperationalZone).where(OperationalZone.activity_id == uuid))

        for zone_data in operational_zones:
            new_zone = OperationalZone(
                activity_id=uuid,
                province=zone_data.province,
                district=zone_data.district,
                created_by=current_user.email
            )
            db.add(new_zone)

        await db.commit()
        await db.refresh(activity)

        return activity

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.patch('/{uuid}/domains', response_model=ActivityRead, dependencies=[Depends(partner_access)])
async def update_activity_domains(
        uuid: uuid.UUID,
        domains: List[ActivityDomainUpdate],
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    try:
        query = select(Activity).where(Activity.uuid == uuid)
        result = await db.execute(query)
        activity = result.scalar_one_or_none()

        if not activity:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail='Activity not found')

        if activity.created_by != current_user.email and current_user.role != UserRole.ADMIN:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail='You are not authorized to perform this action')

        await db.execute(delete(ActivityDomain).where(ActivityDomain.activity_id == uuid))

        for domain_data in domains:
            new_domain = ActivityDomain(
                activity_id=uuid,
                domain_intervention_id=domain_data.domain_intervention_id,
                sub_domain_id=domain_data.sub_domain_id,
                created_by=current_user.email
            )
            db.add(new_domain)

        await db.commit()
        await db.refresh(activity)

        return activity

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.patch('/{uuid}/input_details', response_model=ActivityRead, dependencies=[Depends(partner_access)])
async def update_activity_input_details(
        uuid: uuid.UUID,
        input_details: List[InputDetailUpdate],
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    try:
        query = select(Activity).where(Activity.uuid == uuid)
        result = await db.execute(query)
        activity = result.scalar_one_or_none()

        if not activity:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail='Activity not found')

        if activity.created_by != current_user.email and current_user.role != UserRole.ADMIN:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail='Not authorized to update this activity')

        # Delete existing input details
        await db.execute(delete(InputDetail).where(InputDetail.activity_id == uuid))

        # Add new input details
        for input_data in input_details:
            new_input_detail = InputDetail(
                activity_id=uuid,
                input_category_id=input_data.input_category_id,
                input_id=input_data.input_id,
                budget=input_data.budget,
                district=input_data.district,
                province=input_data.province,
                created_by=current_user.email
            )
            db.add(new_input_detail)

        await db.commit()
        await db.refresh(activity)

        return activity
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get('/{uuid}', response_model=ActivityRead)
async def get_activity(
        uuid: str,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    try:
        query = select(Activity).filter(Activity.uuid == uuid).options(
            joinedload(Activity.project),  # Add any other related models as needed
        )

        activity_result = await db.execute(query)
        activity = activity_result.unique().scalar_one_or_none()

        if not activity:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail='Activity not found')

        # Access control based on user role
        if current_user.role in ['admin', 'swapteam_member']:
            return activity
        elif current_user.role == 'partner' and activity.created_by == current_user.email:
            return activity
        else:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail='You are not authorized to access this activity')

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get('/{uuid}/input_details', response_model=PaginatedResponse[InputDetailRead])
async def get_activity_input_details(
        uuid: uuid.UUID,
        page: int = 1,
        page_size: int = 100,
        db: AsyncSession = Depends(get_db)
):
    query = (select(InputDetail)
             .where(InputDetail.activity_id == uuid)
             .order_by(InputDetail.created_at.desc())
             .offset((page - 1) * page_size)
             .limit(page_size))

    input_details = await db.execute(query)
    input_details_list = input_details.scalars().all()

    if not input_details_list:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No input details found for this activity")

    total_items_query = select(func.count()).select_from(InputDetail).where(InputDetail.activity_id == uuid)
    total_items = (await db.execute(total_items_query)).scalar_one()
    total_pages = (total_items + page_size - 1) // page_size

    return PaginatedResponse(
        page=page,
        page_size=page_size,
        total_items=total_items,
        total_pages=total_pages,
        data=input_details_list
    )


@router.get('/{uuid}/domains', response_model=PaginatedResponse[ActivityDomainDetail])
async def get_activity_domains(
        uuid: uuid.UUID,
        page: int = 1,
        page_size: int = 100,
        db: AsyncSession = Depends(get_db)
):
    query = (select(ActivityDomain)
             .where(ActivityDomain.activity_id == uuid)
             .order_by(ActivityDomain.created_at.desc())
             .offset((page - 1) * page_size)
             .limit(page_size))

    domains = await db.execute(query)
    domains_list = domains.scalars().all()

    if not domains_list:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No domains found for this activity")

    total_items_query = select(func.count()).select_from(ActivityDomain).where(ActivityDomain.activity_id == uuid)
    total_items = (await db.execute(total_items_query)).scalar_one()
    total_pages = (total_items + page_size - 1) // page_size

    return PaginatedResponse(
        page=page,
        page_size=page_size,
        total_items=total_items,
        total_pages=total_pages,
        data=domains_list
    )


@router.get('/{uuid}/operational_zones', response_model=PaginatedResponse[OperationalZoneRead])
async def get_activity_operational_zones(
        uuid: uuid.UUID,
        page: int = 1,
        page_size: int = 100,
        db: AsyncSession = Depends(get_db)
):
    query = (select(OperationalZone)
             .where(OperationalZone.activity_id == uuid)
             .order_by(OperationalZone.created_at.desc())
             .offset((page - 1) * page_size)
             .limit(page_size))

    operational_zones = await db.execute(query)
    operational_zones_list = operational_zones.scalars().all()

    if not operational_zones_list:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No operational zones found for this activity")

    total_items_query = select(func.count()).select_from(OperationalZone).where(OperationalZone.activity_id == uuid)
    total_items = (await db.execute(total_items_query)).scalar_one()
    total_pages = (total_items + page_size - 1) // page_size

    return PaginatedResponse(
        page=page,
        page_size=page_size,
        total_items=total_items,
        total_pages=total_pages,
        data=operational_zones_list
    )


@router.patch('/operational_zone/{uuid}', response_model=OperationalZoneRead, dependencies=[Depends(partner_access)])
async def update_specific_operational_zone(
        uuid: uuid.UUID,
        zone_update: OperationalZoneUpdate,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    try:
        query = select(OperationalZone).where(OperationalZone.uuid == uuid)
        result = await db.execute(query)
        operational_zone = result.scalar_one_or_none()

        if not operational_zone:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail='Operational zone not found')

        if operational_zone.created_by != current_user.email and current_user.role != UserRole.ADMIN:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail='Not authorized to update this operational zone')

        for key, value in zone_update.dict(exclude_unset=True).items():
            setattr(operational_zone, key, value)

        await db.commit()
        await db.refresh(operational_zone)

        return operational_zone
    except Exception as e:
        await db.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.patch('/domain/{uuid}', response_model=ActivityDomainDetail, dependencies=[Depends(partner_access)])
async def update_specific_domain(
        uuid: uuid.UUID,
        domain_update: ActivityDomainUpdate,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    try:
        query = select(ActivityDomain).where(ActivityDomain.uuid == uuid)
        result = await db.execute(query)
        domain = result.scalar_one_or_none()

        if not domain:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail='Domain not found')

        if domain.created_by != current_user.email and current_user.role != UserRole.ADMIN:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail='Not authorized to update this domain')

        for key, value in domain_update.dict(exclude_unset=True).items():
            setattr(domain, key, value)

        await db.commit()
        await db.refresh(domain)

        return domain
    except Exception as e:
        await db.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.patch('/input_detail/{uuid}', response_model=InputDetailRead, dependencies=[Depends(partner_access)])
async def update_specific_input_detail(
        uuid: uuid.UUID,
        input_detail_update: InputDetailUpdate,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    try:
        query = select(InputDetail).where(InputDetail.uuid == uuid)
        result = await db.execute(query)
        input_detail = result.scalar_one_or_none()

        if not input_detail:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail='Input detail not found')

        if input_detail.created_by != current_user.email and current_user.role != UserRole.ADMIN:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail='Not authorized to update this input detail')

        for key, value in input_detail_update.dict(exclude_unset=True).items():
            setattr(input_detail, key, value)

        await db.commit()
        await db.refresh(input_detail)

        return input_detail
    except Exception as e:
        await db.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
