from typing import Optional, List

import uuid
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    Form,
    File,
    UploadFile,
    Query,
)
from sqlalchemy import func, delete
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload, selectinload
from sqlmodel.ext.asyncio.session import AsyncSession

from api.dependencies.access_control import (
    partner_access,
    moh_staff_access,
)
from api.dependencies.auth import get_current_user
from api.dependencies.email_notification_handler import get_email_notification_handler
from db.database import get_db
from db.models import (
    Project,
    MouApplication,
    MouDetail,
    Mou,
    MouComment,
    Party,
    OrganizationType,
    OrganizationFinancingScheme,
)
from db.models.organization import (
    Organization,
    OrganizationFinancingAgent,
    OrganizationHealthCareProvider,
    OrganizationSubFinancingScheme,
    OrganizationSubFinancingAgent,
    OrganizationSubHealthCareProvider,
)
from db.models.document import Document, DocumentType
from db.models.pagination import PaginatedResponse
from db.models.user import User, UserRole
from helpers.comments import filter_comments_for_partner
from helpers.exceptions import handle_integrity_error
from notification.handlers import EmailNotificationHandler
from notification.services import notify_new_user, send_verification_email
from schemas.activity import ActivityRead
from schemas.document import DocumentRead
from schemas.mou import BasicMouReadApplication, BasicMouRead
from schemas.mou_application import MouApplicationProjectRead
from schemas.mou_detail import MouDetailRead
from schemas.organization import OrganizationRead
from schemas.organization_type import OrganizationTypeRead
from schemas.party import PartyRead
from schemas.user import OrganizationUserCreate, OrganizationUser
from helpers.db import check_if_exists, get_all_items, get_first_item
from schemas.project import ProjectRead, ProjectList
from utils.files import handle_upload_file
from utils.security import (
    get_password_hash,
    create_access_token,
    create_verification_token,
)

router = APIRouter()


# TODO: UPDATE TO USE A FORM INSTEAD OF PASSING ALL THE FIELDS HERE (FOR READABILITY PURPOSES)
@router.post("/", response_model=OrganizationRead)
async def create_organization(
    user_email: str = Form(...),
    user_password: str = Form(...),
    user_first_name: str = Form(...),
    user_last_name: str = Form(...),
    user_phone: str = Form(...),
    name: str = Form(...),
    phone_number: str = Form(...),
    email: str = Form(...),
    website: str = Form(...),
    home_country_representative: Optional[str] = Form(None),
    rwanda_representative: str = Form(...),
    home_country: Optional[str] = Form(None),
    home_country_province_state: Optional[str] = Form(None),
    home_country_district: Optional[str] = Form(None),
    home_country_avenue: Optional[str] = Form(None),
    home_country_po_box: Optional[str] = Form(None),
    rwanda_province: str = Form(...),
    rwanda_district: str = Form(...),
    rwanda_avenue: Optional[str] = Form(None),
    rwanda_po_box: Optional[str] = Form(None),
    rgb_number: Optional[str] = Form(None),
    organization_type_id: uuid.UUID = Form(...),
    appointment_letter: UploadFile = File(...),
    notified_constitution_bylaws: UploadFile = None,
    db: AsyncSession = Depends(get_db),
    email_handler: EmailNotificationHandler = Depends(get_email_notification_handler),
):
    if await check_if_exists(Organization, db, name=name):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="Organization with this name already exists",
        )

    if await check_if_exists(User, db, email=user_email):
        raise HTTPException(
            status.HTTP_409_CONFLICT, detail="User with this email already exists"
        )

    hashed_password = get_password_hash(user_password)
    db_user = User(
        email=user_email,
        password=hashed_password,
        first_name=user_first_name,
        last_name=user_last_name,
        phone_number=user_phone,
        role=UserRole.PARTNER,
        created_by=user_email,
    )

    try:
        db.add(db_user)
        await db.commit()
        await db.refresh(db_user)
    except IntegrityError as e:
        await handle_integrity_error(e, db)
    except Exception as e:
        await db.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    # Create organization instance
    new_organization = Organization(
        name=name,
        phone_number=phone_number,
        email=email,
        website=website,
        home_country_representative=home_country_representative,
        rwanda_representative=rwanda_representative,
        home_country=home_country,
        home_country_province_state=home_country_province_state,
        home_country_district=home_country_district,
        home_country_avenue=home_country_avenue,
        home_country_po_box=home_country_po_box,
        rwanda_province=rwanda_province,
        rwanda_district=rwanda_district,
        rwanda_avenue=rwanda_avenue,
        rwanda_po_box=rwanda_po_box,
        rgb_number=rgb_number,
        organization_type_id=organization_type_id,
        created_by=user_email,
    )
    try:
        db.add(new_organization)
        await db.commit()
        await db.refresh(new_organization)

        # Handle file uploads
        appointment_letter_path, appointment_letter_filename = await handle_upload_file(
            appointment_letter
        )
        appointment_letter_doc = Document(
            name="Appointment Letter",
            document_type=DocumentType.APPOINTMENT_LETTER,
            path=appointment_letter_path,
            filename=appointment_letter_filename,
            organization=new_organization,
            created_by=user_email,
        )
        db.add(appointment_letter_doc)

        if notified_constitution_bylaws:
            notified_path, notified_filename = await handle_upload_file(
                notified_constitution_bylaws
            )
            notified_constitution_bylaws_doc = Document(
                name="Notified Constitution Bylaws",
                document_type=DocumentType.NOTIFIED_CONSTITUTION_BYLAWS,
                path=notified_path,
                filename=notified_filename,
                organization=new_organization,
                created_by=user_email,
            )
            db.add(notified_constitution_bylaws_doc)

        await db.commit()
        await notify_new_user(db, email_handler, db_user, new_organization)

        verification_token = create_verification_token(db_user.email)
        await send_verification_email(
            db, email_handler, verification_token=verification_token
        )

    except IntegrityError as e:
        await handle_integrity_error(e, db)
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )
    return new_organization


@router.patch(
    "/{uuid}", response_model=OrganizationRead, dependencies=[Depends(partner_access)]
)
async def update_organization(
    uuid: uuid.UUID,
    name: Optional[str] = Form(None),
    phone_number: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    website: Optional[str] = Form(None),
    home_country_representative: Optional[str] = Form(None),
    rwanda_representative: Optional[str] = Form(None),
    home_country: Optional[str] = Form(None),
    home_country_province_state: Optional[str] = Form(None),
    home_country_district: Optional[str] = Form(None),
    home_country_avenue: Optional[str] = Form(None),
    home_country_po_box: Optional[str] = Form(None),
    rwanda_province: Optional[str] = Form(None),
    rwanda_district: Optional[str] = Form(None),
    rwanda_avenue: Optional[str] = Form(None),
    rwanda_po_box: Optional[str] = Form(None),
    rgb_number: Optional[str] = Form(None),
    organization_type_id: Optional[uuid.UUID] = Form(None),
    appointment_letter: UploadFile = None,
    notified_constitution_bylaws: UploadFile = None,
    financing_schemes: str = Form(),
    financing_agents: str = Form(),
    health_care_providers: str = Form(),
    sub_financing_schemes: str = Form(),
    sub_financing_agents: str = Form(),
    sub_health_care_providers: str = Form(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        query = select(Organization).where(Organization.uuid == uuid)
        result = await db.execute(query)
        organization = result.scalar_one_or_none()

        if not organization:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND, detail="Organization not found"
            )

        if organization.created_by != current_user.email and current_user.role not in [
            UserRole.ADMIN,
            UserRole.DATA_MANAGER,
        ]:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this organization",
            )

        # Update the Organization fields
        organization_data = {
            "name": name,
            "phone_number": phone_number,
            "email": email,
            "website": website,
            "home_country_representative": home_country_representative,
            "rwanda_representative": rwanda_representative,
            "home_country": home_country,
            "home_country_province_state": home_country_province_state,
            "home_country_district": home_country_district,
            "home_country_avenue": home_country_avenue,
            "home_country_po_box": home_country_po_box,
            "rwanda_province": rwanda_province,
            "rwanda_district": rwanda_district,
            "rwanda_avenue": rwanda_avenue,
            "rwanda_po_box": rwanda_po_box,
            "rgb_number": rgb_number,
            "organization_type_id": organization_type_id,
        }

        for key, value in organization_data.items():
            if value is not None:
                setattr(organization, key, value)

        financing_schemes_uuids = [x for x in financing_schemes.split(",") if x]
        financing_agents_uuids = [x for x in financing_agents.split(",") if x]
        health_care_providers_uuids = [x for x in health_care_providers.split(",") if x]
        sub_financing_schemes_uuids = [x for x in sub_financing_schemes.split(",") if x]
        sub_financing_agents_uuids = [x for x in sub_financing_agents.split(",") if x]
        sub_health_care_providers_uuids = [
            x for x in sub_health_care_providers.split(",") if x
        ]

        # Update financing schemes
        await db.execute(
            delete(OrganizationFinancingScheme).where(
                OrganizationFinancingScheme.organization_uuid == uuid
            )
        )
        for scheme_uuid in financing_schemes_uuids:
            db.add(
                OrganizationFinancingScheme(
                    organization_uuid=uuid,
                    financing_scheme_uuid=scheme_uuid,
                    created_by=current_user.email,
                )
            )

        # Update financing agents
        await db.execute(
            delete(OrganizationFinancingAgent).where(
                OrganizationFinancingAgent.organization_uuid == uuid
            )
        )
        for agent_uuid in financing_agents_uuids:
            db.add(
                OrganizationFinancingAgent(
                    organization_uuid=uuid,
                    financing_agent_uuid=agent_uuid,
                    created_by=current_user.email,
                )
            )

        # Update health care providers
        await db.execute(
            delete(OrganizationHealthCareProvider).where(
                OrganizationHealthCareProvider.organization_uuid == uuid
            )
        )
        for provider_uuid in health_care_providers_uuids:
            db.add(
                OrganizationHealthCareProvider(
                    organization_uuid=uuid,
                    health_care_provider_uuid=provider_uuid,
                    created_by=current_user.email,
                )
            )

        # Update sub-financing schemes
        await db.execute(
            delete(OrganizationSubFinancingScheme).where(
                OrganizationSubFinancingScheme.organization_uuid == uuid
            )
        )
        for sub_scheme_uuid in sub_financing_schemes_uuids:
            db.add(
                OrganizationSubFinancingScheme(
                    organization_uuid=uuid,
                    sub_financing_scheme_uuid=sub_scheme_uuid,
                    created_by=current_user.email,
                )
            )

        # Update sub-financing agents
        await db.execute(
            delete(OrganizationSubFinancingAgent).where(
                OrganizationSubFinancingAgent.organization_uuid == uuid
            )
        )
        for sub_agent_uuid in sub_financing_agents_uuids:
            db.add(
                OrganizationSubFinancingAgent(
                    organization_uuid=uuid,
                    sub_financing_agent_uuid=sub_agent_uuid,
                    created_by=current_user.email,
                )
            )

        # Update sub-health care providers
        await db.execute(
            delete(OrganizationSubHealthCareProvider).where(
                OrganizationSubHealthCareProvider.organization_uuid == uuid
            )
        )
        for sub_provider_uuid in sub_health_care_providers_uuids:
            db.add(
                OrganizationSubHealthCareProvider(
                    organization_uuid=uuid,
                    sub_healthcare_provider_uuid=sub_provider_uuid,
                    created_by=current_user.email,
                )
            )

        async def upload_document(
            upload_file: Optional[UploadFile], document_type: DocumentType
        ):
            if upload_file:
                # Check if a document of the same type exists
                existing_doc_query = select(Document).where(
                    Document.organization_id == organization.uuid,
                    Document.document_type == document_type,
                )
                existing_doc_result = await db.execute(existing_doc_query)
                existing_document = existing_doc_result.scalar_one_or_none()

                if existing_document:
                    await db.delete(existing_document)

                file_path, filename = await handle_upload_file(upload_file)
                document = Document(
                    name=filename,
                    document_type=document_type,
                    path=file_path,
                    filename=filename,
                    organization=organization,
                    created_by=current_user.email,
                )
                db.add(document)

        await upload_document(appointment_letter, DocumentType.APPOINTMENT_LETTER)
        await upload_document(
            notified_constitution_bylaws, DocumentType.NOTIFIED_CONSTITUTION_BYLAWS
        )

        await db.commit()
        await db.refresh(organization)

        return organization
    except Exception as e:
        await db.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get(
    "/",
    response_model=PaginatedResponse[OrganizationRead],
    dependencies=[Depends(moh_staff_access)],
)
async def get_organizations(
    page: int = 1, page_size: int = 100, db: AsyncSession = Depends(get_db)
):
    include = [
        "organization_type",
        "documents",
        "financing_schemes",
        "financing_agents",
        "health_care_providers",
        "sub_financing_schemes",
        "sub_financing_agents",
        "sub_health_care_providers",
    ]
    return await get_all_items(
        db, Organization, page=page, page_size=page_size, include=include
    )


@router.get("/{uuid}", response_model=OrganizationRead)
async def get_organization(
    uuid: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = (
        select(Organization)
        .filter(Organization.uuid == uuid)
        .options(
            selectinload(Organization.organization_type),
            selectinload(Organization.documents),
            selectinload(Organization.financing_schemes),
            selectinload(Organization.financing_agents),
            selectinload(Organization.health_care_providers),
            selectinload(Organization.sub_financing_schemes),
            selectinload(Organization.sub_financing_agents),
            selectinload(Organization.sub_health_care_providers),
        )
    )

    organization = await get_first_item(db, query)

    if not organization:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Organization not found")

    organization_type_query = select(OrganizationType).where(
        OrganizationType.uuid == organization.organization_type_id
    )
    organization_type = (await db.execute(organization_type_query)).scalar_one_or_none()

    organization_response = OrganizationRead.from_orm(organization)

    if organization_type:
        organization_response.organization_type = OrganizationTypeRead.from_orm(
            organization_type
        )
    else:
        organization_response.organization_type = None

    documents_query = select(Document).where(
        Document.organization_id == organization.uuid
    )
    documents = (await db.execute(documents_query)).scalars().all()

    organization_response.documents = [DocumentRead.from_orm(doc) for doc in documents]

    if current_user.role in ["admin", "moh_staff"]:
        return organization_response
    elif (
        current_user.role == "partner" and organization.created_by == current_user.email
    ):
        return organization_response
    else:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to perform this action",
        )


@router.post("/{uuid}/user")
async def add_organization_user(
    uuid: uuid.UUID,
    user: OrganizationUserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    if current_user.role != UserRole.PARTNER:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="Only partners can create data managers and data reporters",
        )
    organization_query = select(Organization).filter(Organization.uuid == uuid)
    organization = await get_first_item(db, organization_query)

    if not organization:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Organization not found")

    if user.role not in [UserRole.DATA_MANAGER, UserRole.DATA_REPORTER]:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Invalid role. Must be data_manager or data_reporter",
        )

    if await check_if_exists(User, db, email=user.email):
        raise HTTPException(
            status.HTTP_409_CONFLICT, detail="User with this email already exists"
        )

    hashed_password = get_password_hash(user.password)
    db_user = User(
        email=user.email,
        password=hashed_password,
        first_name=user.first_name,
        last_name=user.last_name,
        role=user.role,
        phone_number=user.phone_number,
        organization_uuid=uuid,
        created_by=current_user.email,
    )

    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)

    token = create_access_token(data={"sub": user.email, "role": user.role})
    return {"user": db_user, "token": {"access_token": token, "token_type": "bearer"}}


@router.get(
    "/{uuid}/mou_applications",
    response_model=PaginatedResponse[MouApplicationProjectRead],
)
async def get_organization_mou_applications(
    uuid: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        # Base query
        base_query = (
            select(
                MouApplication.uuid,
                MouApplication.created_at,
                MouApplication.status,
                MouApplication.modification_entity,
                Project.uuid.label("project_id"),
                Project.name.label("project_name"),
                MouDetail.uuid.label("mou_detail_id"),
                func.array_agg(Party.uuid.distinct()).label("party_ids"),
                func.json_agg(
                    func.json_build_object(
                        "comment",
                        MouComment.content,
                        "created_at",
                        MouComment.created_at,
                        "user",
                        func.json_build_object(
                            "first_name",
                            User.first_name,
                            "last_name",
                            User.last_name,
                            "uuid",
                            User.uuid,
                            "email",
                            User.email,
                            "role",
                            User.role,
                            "level",
                            User.level,
                        ),
                    )
                )
                .filter(MouComment.content.isnot(None))
                .label("comments"),  # Corrected aggregation
            )
            .join(MouApplication.mou_detail)
            .join(MouDetail.project)
            .join(Project.organization)
            .outerjoin(MouDetail.parties)
            .outerjoin(MouApplication.comments)
            .outerjoin(User, MouComment.user_id == User.uuid)  # Join User table
            .filter(Organization.uuid == uuid)
            .group_by(
                MouApplication.uuid,
                MouApplication.created_at,
                MouApplication.status,
                MouApplication.modification_entity,
                Project.uuid,
                Project.name,
                MouDetail.uuid,
            )
        )

        # Apply role-based filtering
        if current_user.role == "partner":
            base_query = base_query.filter(
                MouApplication.created_by == current_user.email
            )
        elif current_user.role not in ["admin", "moh_staff"]:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to access these MOU applications",
            )

        # Count total items
        count_query = select(func.count()).select_from(base_query.subquery())
        total_items = await db.scalar(count_query)

        # Fetch paginated results
        query = (
            base_query.order_by(MouApplication.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await db.execute(query)
        mou_applications = result.all()

        filtered_applications = []
        if current_user.role == UserRole.PARTNER:
            filtered_applications = await filter_comments_for_partner(
                db, mou_applications
            )
        else:
            for app in mou_applications:
                filtered_app = MouApplicationProjectRead(
                    uuid=app.uuid,
                    reference_number=f"{app.created_at:%Y%m%d}-{app.uuid.int % 1000000:06d}",
                    project_name=app.project_name,
                    status=app.status,
                    comments=app.comments,
                    project_id=app.project_id,
                    mou_detail_id=app.mou_detail_id,
                    party_ids=app.party_ids,
                    modification_entities=app.modification_entity,
                )
                filtered_applications.append(filtered_app)

        total_pages = (total_items + page_size - 1) // page_size

        return PaginatedResponse(
            page=page,
            page_size=page_size,
            total_items=total_items,
            total_pages=total_pages,
            data=filtered_applications,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.get(
    "/{organization_uuid}/projects", response_model=PaginatedResponse[ProjectList]
)
async def get_organization_projects(
    organization_uuid: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        # Query to get the organization with its projects
        query = (
            select(Organization)
            .options(selectinload(Organization.projects))
            .filter(Organization.uuid == organization_uuid)
        )

        result = await db.execute(query)
        organization = result.scalar_one_or_none()

        if not organization:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found"
            )

        # Access control based on user role
        if current_user.role not in ["admin", "moh_staff"]:
            if (
                current_user.role == "partner"
                and organization.created_by != current_user.email
            ):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You are not authorized to access these projects",
                )
            elif current_user.role != "partner":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You are not authorized to access these projects",
                )

        # Sort projects by created_at before creating ProjectList objects
        sorted_projects = sorted(
            organization.projects, key=lambda x: x.created_at, reverse=True
        )

        # Convert projects to ProjectList objects
        projects = [
            ProjectList(
                uuid=project.uuid,
                name=project.name,
                description=project.description,
                duration=project.duration,
                currency=project.currency,
                fiscal_year_budgets=project.fiscal_year_budgets,
                total_budget=project.total_budget,
            )
            for project in sorted_projects
        ]

        # Paginate the results
        total_items = len(projects)
        start_index = (page - 1) * page_size
        end_index = start_index + page_size
        projects_paginated = projects[start_index:end_index]

        total_pages = (total_items + page_size - 1) // page_size
        paginated_response = PaginatedResponse(
            page=page,
            page_size=page_size,
            total_items=total_items,
            total_pages=total_pages,
            data=projects_paginated,
        )

        return paginated_response

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.get("/{uuid}/activities", response_model=PaginatedResponse[ActivityRead])
async def get_organization_activities(
    uuid: str,
    page: int = 1,
    page_size: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        # Check if the organization exists and get its activities
        organization_query = (
            select(Organization)
            .filter(Organization.uuid == uuid)
            .options(joinedload(Organization.projects).joinedload(Project.activities))
        )

        organization_result = await db.execute(organization_query)
        organization = organization_result.unique().scalar_one_or_none()

        if not organization:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND, detail="Organization not found"
            )

        # Access control based on user role
        if current_user.role not in ["admin", "moh_staff"]:
            if (
                current_user.role == "partner"
                and organization.created_by != current_user.email
            ):
                raise HTTPException(
                    status.HTTP_403_FORBIDDEN,
                    detail="You are not authorized to access these activities",
                )
            elif (
                current_user.role in [UserRole.DATA_MANAGER, UserRole.DATA_REPORTER]
                and organization.uuid != current_user.organization_uuid
            ):
                raise HTTPException(
                    status.HTTP_403_FORBIDDEN,
                    detail="You are not authorized to access these activities",
                )

        # Gather all activities from the organization's projects and order by most recent
        activities = []
        for project in organization.projects:
            activities.extend(project.activities)
        activities = sorted(activities, key=lambda x: x.created_at, reverse=True)

        total_items = len(activities)
        activities_paginated = activities[(page - 1) * page_size : page * page_size]

        total_pages = (total_items + page_size - 1) // page_size
        paginated_response = PaginatedResponse(
            page=page,
            page_size=page_size,
            total_items=total_items,
            total_pages=total_pages,
            data=activities_paginated,
        )

        return paginated_response

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.get("/{uuid}/mou_details", response_model=PaginatedResponse[MouDetailRead])
async def get_organization_mou_details(
    uuid: str,
    page: int = 1,
    page_size: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        # Fetch the organization with lazy loading
        organization_query = select(Organization).filter(Organization.uuid == uuid)
        organization_result = await db.execute(organization_query)
        organization = organization_result.unique().scalar_one_or_none()

        print("ORGANIZATION: ", organization)

        if not organization:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND, detail="Organization not found"
            )

        # Access control based on user role
        if current_user.role not in ["admin", "moh_staff"]:
            if (
                current_user.role == "partner"
                and organization.created_by != current_user.email
            ):
                raise HTTPException(
                    status.HTTP_403_FORBIDDEN,
                    detail="You are not authorized to access these MOU details",
                )
            elif current_user.role != "partner":
                raise HTTPException(
                    status.HTTP_403_FORBIDDEN,
                    detail="You are not authorized to access these MOU details",
                )

        # Gather all MOU details from the organization's projects and order by most recent
        mou_details = []
        projects_query = select(Project).filter(Project.organization_id == uuid)
        projects_result = await db.execute(projects_query)
        projects = projects_result.scalars().all()

        print("PROJECTS: ", projects)

        for project in projects:
            project_mou_details = (
                select(MouDetail)
                .options(
                    selectinload(MouDetail.parties),
                    selectinload(MouDetail.documents),
                    selectinload(MouDetail.project),
                )
                .filter(MouDetail.project_id == project.uuid)
            )
            project_mou_details_result = await db.execute(project_mou_details)
            project_mou_details_list = project_mou_details_result.scalars().all()

            print("PROJECT MOU DETAILS LIST: ", project_mou_details_list)
            mou_details.extend(project_mou_details_list)

        # Map data to response schema
        response_data = []
        for mou_detail in mou_details:
            project_read = ProjectRead(
                uuid=mou_detail.project.uuid,
                name=mou_detail.project.name,
                # ... other project details (description, budget_type, etc.)
            )
            response_data.append(
                MouDetailRead(
                    uuid=mou_detail.uuid,
                    project=project_read,
                    parties=[
                        PartyRead(**party.__dict__) for party in mou_detail.parties
                    ],
                    documents=[
                        DocumentRead(**document.__dict__)
                        for document in mou_detail.documents
                    ],
                )
            )

        # Pagination
        total_items = len(mou_details)

        total_pages = (total_items + page_size - 1) // page_size
        paginated_response = PaginatedResponse(
            page=page,
            page_size=page_size,
            total_items=total_items,
            total_pages=total_pages,
            data=response_data,
        )

        return paginated_response

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.get("/{organization_uuid}/mous", response_model=PaginatedResponse[BasicMouRead])
async def get_organization_mous(
    organization_uuid: uuid.UUID,
    page: int = 1,
    page_size: int = 10,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        # Check if the organization exists
        organization_query = select(Organization).where(
            Organization.uuid == organization_uuid
        )
        organization_result = await db.execute(organization_query)
        organization = organization_result.scalar_one_or_none()

        if not organization:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND, detail="Organization not found"
            )

        # Authorization check
        if (
            current_user.role != "partner"
            or organization.created_by != current_user.email
        ):
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to access this resource",
            )

        # Fetch the total number of MOUs related to the organization
        total_items_query = (
            select(func.count(Mou.uuid))
            .join(MouApplication)
            .join(MouDetail)
            .where(MouDetail.project.has(Project.organization_id == organization_uuid))
        )
        total_items = (await db.execute(total_items_query)).scalar_one()

        # Fetch the paginated MOUs with lazy loading
        query = (
            select(Mou)
            .options(selectinload(Mou.mou_application))
            .where(MouDetail.project.has(Project.organization_id == organization_uuid))
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await db.execute(query)
        mous = result.scalars().all()

        # Map data to BasicMouRead schema
        response_data = []
        for mou in mous:
            print(mou)
            mou_application_read = BasicMouReadApplication(
                uuid=mou.mou_application.uuid,
                status=mou.mou_application.status,
                reference_number=mou.mou_application.reference_number,
                submitted_by=mou.mou_application.submitted_by,
                last_decision_date=mou.mou_application.last_decision_date,
                modification_entity=mou.mou_application.modification_entity,
            )
            response_data.append(
                BasicMouRead(mou_application=mou_application_read, uuid=mou.uuid)
            )

        total_pages = (total_items + page_size - 1) // page_size
        return PaginatedResponse(
            page=page,
            page_size=page_size,
            total_items=total_items,
            total_pages=total_pages,
            data=response_data,
        )

    except Exception as e:
        print(str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.get("/{organization_uuid}/users", response_model=List[OrganizationUser])
async def get_organization_users(
    organization_uuid: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        # First, check if the organization exists
        org_query = select(Organization).where(Organization.uuid == organization_uuid)
        org_result = await db.execute(org_query)
        organization = org_result.scalar_one_or_none()

        if not organization:
            raise HTTPException(status_code=404, detail="Organization not found")

        # Query for users associated with this organization
        query = select(User).where(User.organization_uuid == organization_uuid)
        result = await db.execute(query)
        users = list(result.scalars().all())

        # Check for the user who created the organization if not already included
        creator_email = organization.created_by
        if creator_email and not any(user.email == creator_email for user in users):
            creator_query = select(User).where(User.email == creator_email)
            creator_result = await db.execute(creator_query)
            creator = creator_result.scalar_one_or_none()
            if creator:
                users.append(creator)

        if not users:
            raise HTTPException(
                status_code=404, detail="No users found for this organization"
            )

        return users
    except HTTPException as he:
        # Re-raise HTTP exceptions to maintain the correct status code
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}",
        )
