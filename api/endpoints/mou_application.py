import uuid
from datetime import datetime
from enum import Enum
from typing import List, Optional

from fastapi import (
    APIRouter,
    Request,
    Depends,
    status,
    HTTPException,
    Query,
    BackgroundTasks,
)
from sqlalchemy import distinct, select, func, and_, or_
from sqlalchemy.orm import joinedload, selectinload
from sqlmodel.ext.asyncio.session import AsyncSession

from api.dependencies.access_control import partner_access, moh_staff_access
from api.dependencies.auth import get_current_user
from api.dependencies.email_notification_handler import get_email_notification_handler
from db.database import get_db
from db.models import (
    User,
    MouDetail,
    MouApplication,
    Document,
    DocumentType,
    UserRole,
    MOHStaffLevel,
    MouApprovalDecision,
    MouApproval,
    MouApplicationStatus,
    MouComment,
    Project,
    Mou,
    MouReview,
    PaginatedResponse,
    Organization,
    Activity,
    ActivityDomain,
    InputDetail,
    Party,
    OrganizationType,
    Input,
    InputCategory,
    DomainIntervention,
    SubDomain,
    FundingSource,
    FundingUnit,
    BudgetType,
)
from db.models.domain import SubDomainFunction, SubFunction
from db.models.mou_approval_or_review import (
    MouApprovalOrReview,
    MouApprovalOrReviewDecision,
)
from db.models.mou_review import MouReviewDecision
from helpers.db import (
    get_first_item,
    get_most_recent_decision_time,
)
from helpers.mou_application import (
    PaginationParams,
    AllApplicationsFilters,
    SortingParams,
    get_filters,
)
from notification.handlers import EmailNotificationHandler
from notification.services import (
    notify_partner_coordinators,
    notify_moh_staff,
    notify_partner,
)
from schemas.comment import MouCommentRead
from schemas.document import DocumentRead
from schemas.mou_application import (
    MouApplicationRead,
    MouApplicationCreate,
    SimpleOrganizationRead,
    MouApplicationOrganizationRead,
)
from schemas.mou_approval import MouApprovalRead, MouApprovalCreate
from schemas.mou_approval_or_review import (
    MouApprovalOrReviewRead,
    UserProfileForApprovalOrReview,
    MouApprovalOrReviewCommentRead,
)
from schemas.mou_detail import MouDetailRead
from schemas.mou_review import MouReviewRead, MouReviewCreate
from utils.files import generate_mou_action_plan, generate_mou_doc, save_mou_doc_to_disk
from utils.filters import parse_uuid_list, parse_string_list
from utils.functions import calculate_time_difference_ms, format_time_difference

router = APIRouter()


@router.post(
    "/", response_model=MouApplicationRead, dependencies=[Depends(partner_access)]
)
async def create_mou_application(
    request: Request,
    mou_application_data: MouApplicationCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    email_handler: EmailNotificationHandler = Depends(get_email_notification_handler),
):
    user = request.state.user.email
    full_name = request.state.user.first_name + " " + request.state.user.last_name

    try:
        query = select(MouDetail).filter(
            MouDetail.uuid == mou_application_data.mou_detail_id
        )

        mou_detail = await get_first_item(db, query)

        if not mou_detail:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Mou detail not found"
            )

        new_mou_application = MouApplication(
            mou_detail_id=mou_application_data.mou_detail_id,
            partner_template_comment=mou_application_data.partner_template_comment,
            created_by=user,
            submitted_by=full_name,
        )

        db.add(new_mou_application)
        await db.commit()
        await db.refresh(new_mou_application)

        file_path, filename = await generate_mou_action_plan(new_mou_application, db)

        excel_document = Document(
            name=f"MOU Application Action Plan - {new_mou_application.id}",
            description="Action Plan Report",
            document_type=DocumentType.ADDITIONAL_DOCUMENT,
            path=file_path,
            filename=filename,
            mou_application=new_mou_application,
            created_by=user,
        )

        db.add(excel_document)
        await db.commit()
        await db.refresh(excel_document)

        mou_detail_query = select(MouDetail).where(
            MouDetail.uuid == new_mou_application.mou_detail_id
        )
        mou_detail = (await db.execute(mou_detail_query)).scalar_one_or_none()

        project_query = (
            select(Project)
            .options(
                selectinload(Project.organization),
            )
            .where(Project.uuid == mou_detail.project_id)
        )
        project = (await db.execute(project_query)).scalar_one_or_none()

        organization_type_query = select(OrganizationType).where(
            OrganizationType.uuid == project.organization.organization_type_id
        )
        organization_type = (
            await db.execute(organization_type_query)
        ).scalar_one_or_none()

        # Generate draft MOU document
        template_path = (
            "mou_templates/mou_international.docx"
            if organization_type.name.lower() == "international ngo"
            else "mou_templates/mou_local.docx"
        )

        docx_buffer, pdf_buffer = await generate_mou_doc(
            new_mou_application, template_path, db
        )

        draft_docx_filename = (
            f"DRAFT_MOU_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"
        )
        draft_docx_filepath, draft_docx_filename = await save_mou_doc_to_disk(
            docx_buffer, draft_docx_filename, "docx"
        )

        draft_pdf_filename = f"DRAFT_MOU_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        draft_pdf_filepath, draft_pdf_filename = await save_mou_doc_to_disk(
            pdf_buffer, draft_pdf_filename, "pdf"
        )

        draft_docx_document = Document(
            name=f"Draft MOU Application - {new_mou_application.id} (DOCX)",
            description="Draft Memorandum of understanding document",
            document_type=DocumentType.ADDITIONAL_DOCUMENT,
            path=draft_docx_filepath,
            filename=draft_docx_filename,
            mou_application=new_mou_application,
            created_by=user,
        )

        draft_pdf_document = Document(
            name=f"Draft MOU Application - {new_mou_application.id}",
            description="Draft Memorandum of understanding document",
            document_type=DocumentType.ADDITIONAL_DOCUMENT,
            path=draft_pdf_filepath,
            filename=draft_pdf_filename,
            mou_application=new_mou_application,
            created_by=user,
        )

        db.add(draft_docx_document)
        db.add(draft_pdf_document)

        await db.commit()
        await db.refresh(excel_document)
        await db.refresh(draft_docx_document)
        await db.refresh(draft_pdf_document)

        await notify_partner_coordinators(
            db,
            str(new_mou_application.id),
            created_by=user,
            email_handler=email_handler,
            background_tasks=background_tasks,
        )
        new_mou_application.mou_detail = mou_detail

        parties_query = select(Party).where(Party.mou_detail_id == mou_detail.uuid)
        parties = (await db.execute(parties_query)).scalars().all()

        project_query = (
            select(Project)
            .where(Project.uuid == mou_detail.project_id)
            .options(selectinload(Project.organization))
        )
        project = (await db.execute(project_query)).scalar_one_or_none()

        documents_query = select(Document).where(
            Document.mou_detail_id == mou_detail.uuid
        )
        documents = (await db.execute(documents_query)).scalars().all()

        if project is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
            )

        mou_detail_read = MouDetailRead(
            uuid=mou_detail.uuid,
            project=project,
            parties=parties,
            documents=documents,  # Add documents if needed
        )

        organization = SimpleOrganizationRead(
            uuid=project.organization.uuid,
            name=project.organization.name,
            email=project.organization.email,
            website=project.organization.website,
            organization_type=organization_type.name,  # Extract the name attribute
        )

        response_data = MouApplicationRead(
            uuid=new_mou_application.uuid,
            status=new_mou_application.status,
            mou_detail=mou_detail_read,
            documents=[
                DocumentRead.from_orm(doc) for doc in new_mou_application.documents
            ],
            comments=[],
            reference_number=new_mou_application.reference_number,
            submitted_by=new_mou_application.submitted_by,
            last_decision_date=new_mou_application.last_decision_date,
            modification_entity=new_mou_application.modification_entity,
            organization=organization,
        )
        return response_data

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.get(
    "/level",
    response_model=PaginatedResponse[MouApplicationOrganizationRead],
    dependencies=[Depends(moh_staff_access)],
)
async def get_level_specific_mou_applications(
    level: Optional[MOHStaffLevel] = Query(
        None, description="Filter applications by level"
    ),
    application_status: Optional[List[MouApplicationStatus]] = Query(
        None, description="Filter applications by status"
    ),
    page: int = 1,
    page_size: int = 100,
    sort_by: Optional[str] = Query(
        None, description="Field to sort by: status, created_at"
    ),
    order: Optional[str] = Query("desc", description="Sort order: asc or desc"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        base_query = (
            select(
                MouApplication.created_at,
                MouApplication.submitted_by,
                MouApplication.uuid,
                MouApplication.status,
                MouApplication.next_level,
                Organization.name.label("organization"),
                OrganizationType.name.label("organization_type"),
            )
            .join(MouApplication.mou_detail)
            .join(MouDetail.project)
            .join(Project.organization)
            .join(Organization.organization_type)
        )

        filters = []

        # Use current_user's level if no specific level is provided
        user_level = level or current_user.level

        if user_level:
            if user_level == MOHStaffLevel.PARTNER_COORDINATOR:
                filters.append(
                    or_(
                        MouApplication.status == MouApplicationStatus.PENDING,
                        MouApplication.next_level == MOHStaffLevel.PARTNER_COORDINATOR,
                    )
                )
            elif user_level in [
                MOHStaffLevel.LEGAL_ADVISOR,
                MOHStaffLevel.TECHNICAL_DEPARTMENT,
            ]:
                filters.append(
                    or_(
                        and_(
                            MouApplication.status == MouApplicationStatus.UNDER_REVIEW,
                            MouApplication.next_level.is_(None),
                        ),
                        MouApplication.next_level == user_level,
                    )
                )
            else:
                filters.append(MouApplication.next_level == user_level)

        if application_status:
            filters.append(MouApplication.status.in_(application_status))

        # Apply all filters
        for filter_condition in filters:
            base_query = base_query.filter(filter_condition)

        # Apply sorting
        if sort_by:
            if sort_by == "status":
                order_by = (
                    MouApplication.status.desc()
                    if order == "desc"
                    else MouApplication.status.asc()
                )
            elif sort_by == "created_at":
                order_by = (
                    MouApplication.created_at.desc()
                    if order == "desc"
                    else MouApplication.created_at.asc()
                )
            else:
                order_by = MouApplication.created_at.desc()  # Default sorting
        else:
            order_by = MouApplication.created_at.desc()  # Default sorting

        base_query = base_query.order_by(order_by)

        # Count query
        count_query = select(func.count()).select_from(base_query.subquery())
        total_items = (await db.execute(count_query)).scalar_one()

        # Paginated query
        paginated_query = base_query.offset((page - 1) * page_size).limit(page_size)

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
            )
            for app in mou_applications
        ]

        return PaginatedResponse(
            page=page,
            page_size=page_size,
            total_items=total_items,
            total_pages=(total_items + page_size - 1) // page_size,
            data=response_data,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.get("/", response_model=PaginatedResponse[MouApplicationOrganizationRead])
async def get_mou_applications(
    pagination: PaginationParams = Depends(PaginationParams),
    filter_params: AllApplicationsFilters = Depends(get_filters),
    sorting: SortingParams = Depends(SortingParams),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        # Parse URL-encoded, comma-separated UUIDs and strings
        organization_uuids = parse_uuid_list(filter_params.organization_uuids)
        funding_source_uuids = parse_uuid_list(filter_params.funding_source_uuids)
        funding_unit_uuids = parse_uuid_list(filter_params.funding_unit_uuids)
        budget_type_uuids = parse_uuid_list(filter_params.budget_type_uuids)
        domain_intervention_uuids = parse_uuid_list(
            filter_params.domain_intervention_uuids
        )
        sub_domain_uuids = parse_uuid_list(filter_params.sub_domain_uuids)
        sub_domain_function_uuids = parse_uuid_list(
            filter_params.sub_domain_function_uuids
        )
        sub_function_uuids = parse_uuid_list(filter_params.sub_function_uuids)
        input_category_uuids = parse_uuid_list(filter_params.input_category_uuids)
        input_uuids = parse_uuid_list(filter_params.input_uuids)
        districts = parse_string_list(filter_params.districts)
        provinces = parse_string_list(filter_params.provinces)
        application_status = parse_string_list(filter_params.application_status)
        print("APPLICATION STATUS: ", application_status)
        next_levels = parse_string_list(filter_params.next_levels)

        # Determine if we need to calculate the budget
        calculate_budget = sorting.sort_by == "budget"

        # Base query
        base_query = select(
            MouApplication.created_at,
            MouApplication.submitted_by,
            MouApplication.uuid,
            MouApplication.status,
            MouApplication.next_level,
            Organization.name.label("organization"),
            OrganizationType.name.label("organization_type"),
        )

        # Add budget calculation only if needed
        if calculate_budget:
            budget_subquery = (
                select(
                    Activity.project_id,
                    func.sum(InputDetail.budget).label("total_budget"),
                )
                .join(InputDetail.activity)
                .group_by(Activity.project_id)
                .subquery()
            )
            base_query = base_query.add_columns(
                func.coalesce(budget_subquery.c.total_budget, 0).label("total_budget")
            )

        # Join tables
        base_query = (
            base_query.join(MouApplication.mou_detail)
            .join(MouDetail.project)
            .join(Project.organization)
            .join(Organization.organization_type)
        )

        if calculate_budget:
            base_query = base_query.outerjoin(
                budget_subquery, Project.uuid == budget_subquery.c.project_id
            )

        # Additional joins for filtering and search
        base_query = (
            base_query.join(Project.activities)
            .join(Activity.domains)
            .join(Activity.input_details)
            .join(InputDetail.input)
            .join(InputDetail.input_category)
            .join(ActivityDomain.domain_intervention)
            .join(ActivityDomain.sub_domain)
            .join(ActivityDomain.sub_domain_function)
            .join(ActivityDomain.sub_function)
            .join(Project.funding_source)
            .join(Project.funding_unit)
            .join(Project.budget_type)
        )

        # Group by
        group_by_columns = [
            MouApplication.uuid,
            MouApplication.created_at,
            MouApplication.submitted_by,
            MouApplication.status,
            MouApplication.next_level,
            Organization.name,
            OrganizationType.name,
        ]
        if calculate_budget:
            group_by_columns.append(budget_subquery.c.total_budget)
        base_query = base_query.group_by(*group_by_columns)

        # Apply filters
        filters = []

        if current_user.role == "partner":
            filters.append(MouApplication.created_by == current_user.email)

        # Apply list filters properly
        if organization_uuids:
            filters.append(Project.organization_id.in_(organization_uuids))
        if funding_source_uuids:
            filters.append(Project.funding_source_id.in_(funding_source_uuids))
        if funding_unit_uuids:
            filters.append(Project.funding_unit_id.in_(funding_unit_uuids))
        if budget_type_uuids:
            filters.append(Project.budget_type_id.in_(budget_type_uuids))
        if domain_intervention_uuids:
            filters.append(
                ActivityDomain.domain_intervention_id.in_(domain_intervention_uuids)
            )
        if sub_domain_uuids:
            filters.append(ActivityDomain.sub_domain_id.in_(sub_domain_uuids))
        if sub_domain_function_uuids:
            filters.append(
                ActivityDomain.sub_domain_function_id.in_(sub_domain_function_uuids)
            )
        if sub_function_uuids:
            filters.append(ActivityDomain.sub_function_id.in_(sub_function_uuids))
        if input_category_uuids:
            filters.append(InputDetail.input_category_id.in_(input_category_uuids))
        if input_uuids:
            filters.append(InputDetail.input_id.in_(input_uuids))
        if districts:
            filters.append(InputDetail.district.in_(districts))
        if provinces:
            filters.append(InputDetail.province.in_(provinces))
        if application_status:
            filters.append(
                MouApplication.status.in_(application_status)
            )  # Correctly handle the list
        if next_levels:
            next_level_filter = []
            for level in next_levels:
                if level == MOHStaffLevel.PARTNER_COORDINATOR.value:
                    next_level_filter.append(
                        or_(
                            MouApplication.status == MouApplicationStatus.PENDING,
                            MouApplication.next_level
                            == MOHStaffLevel.PARTNER_COORDINATOR,
                        )
                    )
                elif level in [
                    MOHStaffLevel.LEGAL_ADVISOR.value,
                    MOHStaffLevel.TECHNICAL_DEPARTMENT.value,
                ]:
                    next_level_filter.append(
                        or_(
                            and_(
                                MouApplication.status
                                == MouApplicationStatus.UNDER_REVIEW,
                                MouApplication.next_level.is_(None),
                            ),
                            MouApplication.next_level == level,
                        )
                    )
                else:
                    next_level_filter.append(MouApplication.next_level == level)
            filters.append(or_(*next_level_filter))

        # Add date range filter
        filters.append(MouApplication.created_at >= filter_params.start_date)
        filters.append(MouApplication.created_at <= filter_params.end_date)

        # Add search functionality
        if filter_params.search:
            search_filter = or_(
                Organization.name.ilike(f"%{filter_params.search}%"),
                Activity.name.ilike(f"%{filter_params.search}%"),
                Input.name.ilike(f"%{filter_params.search}%"),
                InputCategory.name.ilike(f"%{filter_params.search}%"),
                DomainIntervention.name.ilike(f"%{filter_params.search}%"),
                SubDomain.name.ilike(f"%{filter_params.search}%"),
                SubDomainFunction.name.ilike(f"%{filter_params.search}%"),
                SubFunction.name.ilike(f"%{filter_params.search}%"),
                FundingSource.name.ilike(f"%{filter_params.search}%"),
                FundingUnit.name.ilike(f"%{filter_params.search}%"),
                BudgetType.name.ilike(f"%{filter_params.search}%"),
            )
            filters.append(search_filter)

        print("FILTERS: ", filters)
        # Apply all filters to the base query
        for filter_condition in filters:
            print("FILTER CONDITION: ", filter_condition)
            base_query = base_query.filter(filter_condition)

        count_query = select(func.count(distinct(MouApplication.uuid))).select_from(
            base_query.with_only_columns(MouApplication.uuid).subquery()
        )
        total_items = (await db.execute(count_query)).scalar_one()

        # Apply sorting
        if sorting.sort_by:
            if sorting.sort_by == "status":
                order_by = (
                    MouApplication.status.desc()
                    if sorting.order == "desc"
                    else MouApplication.status.asc()
                )
            elif sorting.sort_by == "budget":
                order_by = (
                    budget_subquery.c.total_budget.desc()
                    if sorting.order == "desc"
                    else budget_subquery.c.total_budget.asc()
                )
            elif sorting.sort_by == "created_at":
                order_by = (
                    MouApplication.created_at.desc()
                    if sorting.order == "desc"
                    else MouApplication.created_at.asc()
                )
            else:
                order_by = MouApplication.created_at.desc()  # Default sorting
        else:
            order_by = MouApplication.created_at.desc()  # Default sorting

        base_query = base_query.order_by(order_by)

        paginated_query = base_query.offset(
            (pagination.page - 1) * pagination.page_size
        ).limit(pagination.page_size)

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
                total_budget=app.total_budget if calculate_budget else None,
            )
            for app in mou_applications
        ]

        return PaginatedResponse(
            page=pagination.page,
            page_size=pagination.page_size,
            total_items=total_items,
            total_pages=(total_items + pagination.page_size - 1)
            // pagination.page_size,
            data=response_data,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.get("/{uuid}")
async def get_mou_application(
    uuid: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        query = (
            select(MouApplication)
            .options(
                joinedload(MouApplication.mou_detail)
                .joinedload(MouDetail.project)
                .joinedload(Project.organization)
            )
            .where(MouApplication.uuid == uuid)
        )

        result = await db.execute(query)
        mou_application = result.unique().scalar_one_or_none()

        if not mou_application:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND, detail="MOU application not found"
            )

        organization_documents_query = select(Document).where(
            Document.organization_id
            == mou_application.mou_detail.project.organization.uuid
        )
        organization_documents = (
            (await db.execute(organization_documents_query)).scalars().all()
        )

        application_documents_query = select(Document).where(
            Document.mou_application_id == mou_application.uuid
        )
        application_documents = (
            (await db.execute(application_documents_query)).scalars().all()
        )

        mou_detail_documents_query = select(Document).where(
            Document.mou_detail_id == mou_application.mou_detail_id
        )
        mou_detail_documents = (
            (await db.execute(mou_detail_documents_query)).scalars().all()
        )

        all_documents = (
            organization_documents + application_documents + mou_detail_documents
        )
        formatted_documents = [
            {
                "name": doc.filename,
                "path": doc.path,
                "document_type": (
                    doc.document_type.value
                    if isinstance(doc.document_type, Enum)
                    else str(doc.document_type)
                ),
            }
            for doc in all_documents
        ]

        comments_query = (
            select(MouComment)
            .where(MouComment.mou_application_id == mou_application.uuid)
            .options(selectinload(MouComment.user))
        )
        comments = (await db.execute(comments_query)).scalars().all()

        formatted_comments = [
            {
                "comment": comment.content,
                "created_at": comment.created_at,
                "user": {
                    "first_name": comment.user.first_name,
                    "last_name": comment.user.last_name,
                    "uuid": comment.user.uuid,
                    "email": comment.user.email,
                    "role": comment.user.role,
                    "level": comment.user.level,
                },
            }
            for comment in comments
        ]

        if current_user.role in [
            UserRole.ADMIN,
            UserRole.MOH_STAFF,
            UserRole.DATA_MANAGER,
        ] or (
            current_user.role == UserRole.PARTNER
            and mou_application.created_by == current_user.email
        ):
            return {
                "next_level": mou_application.next_level,
                "organization_uuid": mou_application.mou_detail.project.organization.uuid,
                "mou_detail_id": mou_application.mou_detail_id,
                "project_uuid": mou_application.mou_detail.project.uuid,
                "last_decision_date": mou_application.last_decision_date,
                "modification_entity": mou_application.modification_entity,
                "currency": mou_application.mou_detail.project.currency,
                "status": mou_application.status,
                "documents": formatted_documents,
                "partner_template_comment": mou_application.partner_template_comment,
                "comments": formatted_comments,
            }
        else:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to access this MOU application",
            )

    except Exception as e:
        # Log the exception
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.patch(
    "/{uuid}/start_review",
    response_model=MouApplicationRead,
    dependencies=[Depends(moh_staff_access)],
)
async def start_review(
    uuid: str,
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    email_handler: EmailNotificationHandler = Depends(get_email_notification_handler),
):
    user = request.state.user
    if (
        user.role != UserRole.MOH_STAFF
        or user.level != MOHStaffLevel.PARTNER_COORDINATOR
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to perform this action",
        )

    try:
        query = select(MouApplication).filter(MouApplication.uuid == uuid)
        mou_application = await get_first_item(db, query)

        if not mou_application:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="MOU application not found",
            )

        if mou_application.status != MouApplicationStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="MOU application is not in a pending state",
            )

        mou_application.status = MouApplicationStatus.UNDER_REVIEW
        mou_application.last_decision_date = datetime.now()
        mou_application.last_updated_at = datetime.now()

        await db.commit()
        await db.refresh(mou_application)

        await notify_moh_staff(
            db,
            email_handler,
            levels=[MOHStaffLevel.LEGAL_ADVISOR, MOHStaffLevel.TECHNICAL_DEPARTMENT],
            created_by=user.email,
            subject="MOU Application Review Started",
            message=f"An MOU application (ID: {mou_application.id}) has been set to 'Under Review' and requires your attention.",
            background_tasks=background_tasks,
        )

        mou_detail_query = select(MouDetail).where(
            MouDetail.uuid == mou_application.mou_detail_id
        )
        mou_detail = (await db.execute(mou_detail_query)).scalar_one_or_none()

        project_query = (
            select(Project)
            .options(selectinload(Project.organization))
            .where(Project.uuid == mou_detail.project_id)
        )
        project = (await db.execute(project_query)).scalar_one_or_none()

        project_organization = project.organization

        organization_type_id = project_organization.organization_type_id

        organization_type_query = select(OrganizationType).where(
            OrganizationType.uuid == organization_type_id
        )
        organization_type = (
            await db.execute(organization_type_query)
        ).scalar_one_or_none()

        parties_query = select(Party).where(Party.mou_detail_id == mou_detail.uuid)
        parties = (await db.execute(parties_query)).scalars().all()

        documents_query = select(Document).where(
            Document.mou_detail_id == mou_detail.uuid
        )
        documents = (await db.execute(documents_query)).scalars().all()

        mou_detail_read = MouDetailRead(
            uuid=mou_detail.uuid, project=project, parties=parties, documents=documents
        )

        organization = SimpleOrganizationRead(
            uuid=project.organization.uuid,
            name=project.organization.name,
            email=project.organization.email,
            website=project.organization.website,
            organization_type=organization_type.name,
        )

        response_data = MouApplicationRead(
            uuid=mou_application.uuid,
            status=mou_application.status,
            mou_detail=mou_detail_read,
            comments=[],
            reference_number=mou_application.reference_number,
            submitted_by=mou_application.submitted_by,
            last_decision_date=mou_application.last_decision_date,
            modification_entity=mou_application.modification_entity,
            organization=organization,
        )

        return response_data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.get("/{uuid}/approvals", response_model=PaginatedResponse[MouApprovalRead])
async def get_mou_application_approvals(
    uuid: str,
    page: int = 1,
    page_size: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        # Check if the MOU application exists
        query = select(MouApplication).filter(MouApplication.uuid == uuid)
        mou_application_result = await db.execute(query)
        mou_application = mou_application_result.scalar_one_or_none()

        if not mou_application:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND, detail="MOU application not found"
            )

        # Query to get approvals
        approval_query = (
            select(MouApproval)
            .options(joinedload(MouApproval.current_approver))
            .options(joinedload(MouApproval.comments).joinedload(MouComment.user))
            .filter(MouApproval.mou_application_id == uuid)
            .order_by(MouApproval.created_at.desc())
        )
        total_items_query = select(func.count()).select_from(approval_query.subquery())
        total_items = (await db.execute(total_items_query)).scalar_one()

        approvals_result = await db.execute(
            approval_query.offset((page - 1) * page_size).limit(page_size)
        )
        approvals = approvals_result.scalars().unique().all()

        response_data = []

        for approval in approvals:
            current_approver = approval.current_approver
            comments = [
                MouApprovalOrReviewCommentRead(
                    uuid=comment.uuid,
                    content=comment.content,
                    created_at=comment.created_at,
                    created_by=comment.created_by,
                )
                for comment in approval.comments
            ]

            current_approver_read = None
            if current_approver:
                current_approver_read = UserProfileForApprovalOrReview(
                    uuid=current_approver.uuid,
                    first_name=current_approver.first_name,
                    last_name=current_approver.last_name,
                    email=current_approver.email,
                    role=current_approver.role,
                    level=current_approver.level,
                )

            processing_time_dict = format_time_difference(approval.processing_time)

            approval_read = MouApprovalRead(
                uuid=approval.uuid,
                decision=approval.decision,
                comment=comments[0].content if comments else None,
                created_at=approval.created_at,
                current_approver=current_approver_read,
                processing_time=processing_time_dict,
            )

            response_data.append(approval_read)

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


@router.post(
    "/{uuid}/review",
    response_model=MouReviewRead,
    dependencies=[Depends(moh_staff_access)],
)
async def add_review(
    uuid: uuid.UUID,
    review: MouReviewCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    email_handler: EmailNotificationHandler = Depends(get_email_notification_handler),
):
    try:
        query = select(MouApplication).where(MouApplication.uuid == uuid)
        result = await db.execute(query)
        mou_application = result.scalar_one_or_none()

        if not mou_application:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND, detail="MOU application not found"
            )

        # Initial review checks
        if mou_application.next_level is None:
            # New application
            if current_user.level not in [
                MOHStaffLevel.TECHNICAL_DEPARTMENT,
                MOHStaffLevel.LEGAL_ADVISOR,
            ]:
                raise HTTPException(
                    status.HTTP_403_FORBIDDEN,
                    detail="Only technical department or legal advisor can review a new application",
                )

            # Handle initial reviews
            if review.decision == MouReviewDecision.REJECT:
                raise HTTPException(
                    status.HTTP_403_FORBIDDEN,
                    detail="Only partner coordinator is allowed to reject an application in the review stage",
                )
            if review.decision == MouReviewDecision.VERIFIED:
                next_level = (
                    MOHStaffLevel.LEGAL_ADVISOR
                    if current_user.level == MOHStaffLevel.TECHNICAL_DEPARTMENT
                    else MOHStaffLevel.TECHNICAL_DEPARTMENT
                )
            elif review.decision == MouReviewDecision.REQUEST_MODIFICATION:
                next_level = MOHStaffLevel.PARTNER_COORDINATOR
            else:
                raise HTTPException(
                    status.HTTP_403_FORBIDDEN,
                    detail="Invalid decision for the initial review",
                )

        else:
            # Application with reviews
            if current_user.level != mou_application.next_level:
                raise HTTPException(
                    status.HTTP_403_FORBIDDEN,
                    detail="You are not authorized to make decisions at this level",
                )

            if current_user.level == MOHStaffLevel.PARTNER_COORDINATOR:
                if review.decision == MouReviewDecision.RECOMMEND_APPROVAL:
                    mou_application.status = MouApplicationStatus.UNDER_APPROVAL
                    next_level = MOHStaffLevel.HOD
                elif review.decision == MouReviewDecision.REQUEST_MODIFICATION:
                    mou_application.status = MouApplicationStatus.REQUEST_MODIFICATION
                    if review.modification_entity:
                        mou_application.modification_entity = (
                            review.modification_entity
                        )  # Store the list directly
                        # Ensure next level is not stuck at partner coordinator
                        next_level = MOHStaffLevel.PARTNER_COORDINATOR
                elif review.decision == MouReviewDecision.REJECT:
                    mou_application.status = MouApplicationStatus.REJECTED
                    next_level = None
                else:
                    raise HTTPException(
                        status.HTTP_403_FORBIDDEN,
                        detail="Invalid decision for partner coordinator",
                    )

            elif current_user.level in [
                MOHStaffLevel.TECHNICAL_DEPARTMENT,
                MOHStaffLevel.LEGAL_ADVISOR,
            ]:
                if review.decision == MouReviewDecision.VERIFIED:
                    if (
                        not mou_application.next_level
                    ):  # Only set next_level if it is currently null
                        next_level = (
                            MOHStaffLevel.LEGAL_ADVISOR
                            if current_user.level == MOHStaffLevel.TECHNICAL_DEPARTMENT
                            else MOHStaffLevel.TECHNICAL_DEPARTMENT
                        )
                    else:
                        next_level = MOHStaffLevel.PARTNER_COORDINATOR
                elif review.decision == MouReviewDecision.REQUEST_MODIFICATION:
                    next_level = MOHStaffLevel.PARTNER_COORDINATOR
                else:
                    raise HTTPException(
                        status.HTTP_403_FORBIDDEN,
                        detail="Invalid decision for technical department or legal advisor",
                    )

        previous_decision_time = await get_most_recent_decision_time(db, uuid)
        processing_time_ms = calculate_time_difference_ms(
            previous_decision_time, datetime.now()
        )

        # Record the review
        new_review = MouReview(
            mou_application_id=uuid,
            decision=review.decision,
            current_review_id=current_user.uuid,
            created_by=current_user.email,
            processing_time=processing_time_ms,
        )
        db.add(new_review)
        await db.commit()
        await db.refresh(new_review)

        # Record the comment if any
        comment_content = None
        if review.comment:
            new_comment = MouComment(
                content=review.comment,
                user_id=current_user.uuid,
                mou_application_id=uuid,
                mou_review_id=new_review.uuid,
                created_by=current_user.email,
            )
            db.add(new_comment)
            await db.commit()
            await db.refresh(new_comment)
            comment_content = new_comment.content

        # Update MOU application with the latest review details
        mou_application.current_reviewer_id = current_user.uuid
        mou_application.last_decision_date = datetime.now()
        mou_application.next_level = next_level

        await db.commit()
        await db.refresh(mou_application)

        if mou_application.next_level:
            await notify_moh_staff(
                db,
                email_handler,
                levels=[mou_application.next_level],
                created_by=current_user.email,
                subject="MOU Application Requires Your Review",
                message=f"An MOU application (ID: {mou_application.id}) has been reviewed and requires your attention.",
                background_tasks=background_tasks,
            )

        if review.decision == MouReviewDecision.REJECT:
            await notify_partner(
                db,
                email_handler,
                mou_application.id,
                created_by=current_user.email,
                subject="MOU Application Rejected",
                message=f"Your MOU application (ID: {mou_application.id}) has been rejected.",
                background_tasks=background_tasks,
            )
        elif review.decision == MouReviewDecision.REQUEST_MODIFICATION:
            await notify_partner(
                db,
                email_handler,
                mou_application.uuid,
                created_by=current_user.email,
                subject="MOU Application Requires Modification",
                message=f"Your MOU application (ID: {mou_application.id}) requires modifications. Please review and update accordingly.",
                background_tasks=background_tasks,
            )

        return MouReviewRead(
            uuid=new_review.uuid,
            decision=new_review.decision,
            comment=comment_content,
            created_at=new_review.created_at,
            created_by=new_review.created_by,
            current_reviewer=current_user,
            next_level=mou_application.next_level,
            last_decision_date=mou_application.last_decision_date,
        )
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.post(
    "/{uuid}/approval",
    response_model=MouApprovalRead,
    dependencies=[Depends(moh_staff_access)],
)
async def add_approval(
    uuid: uuid.UUID,
    approval: MouApprovalCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    email_handler: EmailNotificationHandler = Depends(get_email_notification_handler),
):
    try:
        query = select(MouApplication).where(MouApplication.uuid == uuid)
        result = await db.execute(query)
        mou_application = result.scalar_one_or_none()

        if not mou_application:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND, detail="MOU application not found"
            )

        # Define the allowed decisions for the approval stage
        approval_stage_decisions = [
            MouApprovalDecision.APPROVE,
            MouApprovalDecision.REJECT,
            MouApprovalDecision.REQUEST_MODIFICATION,
        ]

        approval_stage_levels = [
            MOHStaffLevel.HOD,
            MOHStaffLevel.LEGAL_ADVISOR,
            MOHStaffLevel.PS,
            MOHStaffLevel.MINISTER,
            # MOHStaffLevel.MINISTER_OF_STATE,
        ]

        # Check if the current user is allowed to make the decision
        if current_user.level not in approval_stage_levels:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to make decisions in the approval stage",
            )

        if approval.decision not in approval_stage_decisions:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                detail="Invalid decision for the approval stage",
            )

        if (
            mou_application.next_level
            and current_user.level != mou_application.next_level
        ):
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to make decisions at this level",
            )

        # Handle decisions in the approval stage
        if approval.decision == MouApprovalDecision.APPROVE:
            if current_user.level == MOHStaffLevel.MINISTER:
                mou_detail_query = select(MouDetail).where(
                    MouDetail.uuid == mou_application.mou_detail_id
                )
                mou_detail = (await db.execute(mou_detail_query)).scalar_one_or_none()

                project_query = (
                    select(Project)
                    .options(
                        selectinload(Project.organization),
                    )
                    .where(Project.uuid == mou_detail.project_id)
                )
                project = (await db.execute(project_query)).scalar_one_or_none()

                organization_type_query = select(OrganizationType).where(
                    OrganizationType.uuid == project.organization.organization_type_id
                )
                organization_type = (
                    await db.execute(organization_type_query)
                ).scalar_one_or_none()

                template_path = (
                    "mou_templates/mou_international.docx"
                    if organization_type.name.lower() == "international ngo"
                    else "mou_templates/mou_local.docx"
                )

                docx_buffer, pdf_buffer = await generate_mou_doc(
                    mou_application, template_path, db
                )

                docx_filename = f"MOU_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"
                docx_filepath, docx_filename = await save_mou_doc_to_disk(
                    docx_buffer, docx_filename, "docx"
                )

                pdf_filename = f"MOU_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
                pdf_filepath, pdf_filename = await save_mou_doc_to_disk(
                    pdf_buffer, pdf_filename, "pdf"
                )

                new_docx_document = Document(
                    name=f"MOU Application - {mou_application.id} (DOCX)",
                    description="Memorandum of understanding document",
                    document_type=DocumentType.MOU,
                    path=docx_filepath,
                    filename=docx_filename,
                    mou_application_id=uuid,
                    created_by=current_user.email,
                )

                new_pdf_document = Document(
                    name=f"MOU Application - {mou_application.id}",
                    description="Memorandum of understanding document",
                    document_type=DocumentType.MOU,
                    path=pdf_filepath,
                    filename=pdf_filename,
                    mou_application_id=uuid,
                    created_by=current_user.email,
                )

                db.add(new_docx_document)
                db.add(new_pdf_document)
                await db.commit()
                await db.refresh(new_docx_document)
                await db.refresh(new_pdf_document)

                mou_application.status = MouApplicationStatus.APPROVED
                mou_application.next_level = None

                new_mou = Mou(
                    mou_application_id=uuid,
                    mou_detail_id=mou_application.mou_detail_id,
                    document_id=new_pdf_document.uuid,  # Use PDF as the primary document
                    created_by=current_user.email,
                )

                db.add(new_mou)
                await db.commit()
                await db.refresh(new_mou)

                await notify_partner(
                    db,
                    email_handler,
                    mou_application.uuid,
                    created_by=current_user.email,
                    subject="MOU Application Approved",
                    message=f"Your MOU application (ID: {mou_application.id}) has been approved. Please find the attached MOU document.",
                    attachment_path=pdf_filepath,
                    attachment_filename=pdf_filename,
                    background_tasks=background_tasks,
                )
            else:
                next_level_index = approval_stage_levels.index(current_user.level) + 1
                mou_application.next_level = approval_stage_levels[next_level_index]

                await notify_moh_staff(
                    db,
                    email_handler,
                    created_by=current_user.email,
                    levels=[mou_application.next_level],
                    subject="MOU Application Requires Your Approval",
                    message=f"An MOU application (ID: {mou_application.id}) has been approved at the previous level and requires your attention.",
                    background_tasks=background_tasks,
                )
        elif approval.decision == MouApprovalDecision.REQUEST_MODIFICATION:
            mou_application.status = MouApplicationStatus.UNDER_REVIEW
            mou_application.next_level = MOHStaffLevel.PARTNER_COORDINATOR
            await notify_moh_staff(
                db,
                email_handler,
                created_by=current_user.email,
                levels=[MOHStaffLevel.PARTNER_COORDINATOR],
                subject="MOU Application Requires Modification",
                message=f"An MOU application (ID: {mou_application.id}) requires modification. Please review and coordinate with the partner.",
                background_tasks=background_tasks,
            )
        elif approval.decision == MouApprovalDecision.REJECT:
            mou_application.status = MouApplicationStatus.UNDER_REVIEW
            mou_application.next_level = MOHStaffLevel.PARTNER_COORDINATOR

            # Notify partner coordinator about rejection
            await notify_moh_staff(
                db,
                email_handler,
                created_by=current_user.email,
                levels=[MOHStaffLevel.PARTNER_COORDINATOR],
                subject="MOU Application Rejected",
                message=f"An MOU application (ID: {mou_application.id}) has been rejected. Please review and take appropriate action.",
                background_tasks=background_tasks,
            )

        # Record the approval
        previous_decision_time = await get_most_recent_decision_time(db, uuid)
        processing_time_ms = calculate_time_difference_ms(
            previous_decision_time, datetime.now()
        )

        new_approval = MouApproval(
            mou_application_id=uuid,
            decision=approval.decision,
            current_approver_id=current_user.uuid,
            created_by=current_user.email,
            processing_time=processing_time_ms,
        )
        db.add(new_approval)
        await db.commit()
        await db.refresh(new_approval)

        # Record the comment if any
        comment_content = None
        if approval.comment:
            new_comment = MouComment(
                content=approval.comment,
                user_id=current_user.uuid,
                mou_application_id=uuid,
                mou_approval_id=new_approval.uuid,
                created_by=current_user.email,
            )
            db.add(new_comment)
            await db.commit()
            await db.refresh(new_comment)
            comment_content = new_comment.content

        # Update MOU application with the latest approval details
        mou_application.current_reviewer_id = current_user.uuid
        mou_application.last_decision_date = datetime.now()

        await db.commit()
        await db.refresh(mou_application)

        return MouApprovalRead(
            uuid=new_approval.uuid,
            decision=new_approval.decision,
            comment=comment_content,
            created_at=new_approval.created_at,
            created_by=new_approval.created_by,
            current_reviewer=current_user,
            next_level=mou_application.next_level,
            last_decision_date=mou_application.last_decision_date,
        )
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.get("/{uuid}/reviews", response_model=PaginatedResponse[MouReviewRead])
async def get_mou_application_reviews(
    uuid: uuid.UUID,
    page: int = 1,
    page_size: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        # Check if the MOU application exists
        query = select(MouApplication).filter(MouApplication.uuid == uuid)
        mou_application_result = await db.execute(query)
        mou_application = mou_application_result.scalar_one_or_none()

        if not mou_application:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND, detail="MOU application not found"
            )

        # Query to get reviews
        review_query = (
            select(MouReview)
            .options(joinedload(MouReview.current_reviewer))
            .options(joinedload(MouReview.comments).joinedload(MouComment.user))
            .filter(MouReview.mou_application_id == uuid)
            .order_by(MouReview.created_at.desc())
        )

        total_items_query = select(func.count()).select_from(review_query.subquery())
        total_items = (await db.execute(total_items_query)).scalar_one()

        reviews_result = await db.execute(
            review_query.offset((page - 1) * page_size).limit(page_size)
        )
        reviews = reviews_result.scalars().unique().all()

        response_data = []

        for review in reviews:
            current_reviewer = review.current_reviewer
            comments = [
                MouApprovalOrReviewCommentRead(
                    uuid=comment.uuid,
                    content=comment.content,
                    created_at=comment.created_at,
                    created_by=comment.created_by,
                )
                for comment in review.comments
            ]

            current_reviewer_read = None
            if current_reviewer:
                current_reviewer_read = UserProfileForApprovalOrReview(
                    uuid=current_reviewer.uuid,
                    first_name=current_reviewer.first_name,
                    last_name=current_reviewer.last_name,
                    email=current_reviewer.email,
                    role=current_reviewer.role,
                    level=current_reviewer.level,
                )

            processing_time_dict = format_time_difference(review.processing_time)

            review_read = MouReviewRead(
                uuid=review.uuid,
                decision=review.decision,
                comment=comments[0].content if comments else None,
                created_at=review.created_at,
                current_reviewer=current_reviewer_read,
                processing_time=processing_time_dict,
            )

            response_data.append(review_read)

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


@router.get("/{uuid}/comments", response_model=List[MouCommentRead])
async def get_application_comments(
    uuid: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        # Fetch the MOU application to ensure it exists and the user has access
        query = select(MouApplication).where(MouApplication.uuid == uuid)
        result = await db.execute(query)
        mou_application = result.scalar_one_or_none()

        if not mou_application:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND, detail="MOU application not found"
            )

        if (
            current_user.role not in ["admin", "moh_staff"]
            and mou_application.created_by != current_user.email
        ):
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to access this MOU application",
            )

        # Fetch the comments related to the MOU application
        comments_query = (
            select(MouComment)
            .options(
                selectinload(MouComment.user),
                selectinload(MouComment.mou_application).selectinload(
                    MouApplication.mou_detail
                ),
            )
            .where(MouComment.mou_application_id == uuid)
        )
        comments_result = await db.execute(comments_query)
        comments = comments_result.scalars().all()

        return comments
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.get(
    "/{uuid}/approval_or_review",
    response_model=PaginatedResponse[MouApprovalOrReviewRead],
)
async def get_mou_application_approvals_or_reviews(
    uuid: uuid.UUID,
    page: int = 1,
    page_size: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        # Check if the MOU application exists
        query = select(MouApplication).filter(MouApplication.uuid == uuid)
        mou_application_result = await db.execute(query)
        mou_application = mou_application_result.scalar_one_or_none()

        if not mou_application:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND, detail="MOU application not found"
            )

        # Query to get approvals or reviews with eager loading of current_reviewer and comments
        approval_or_review_query = (
            select(MouApprovalOrReview)
            .options(joinedload(MouApprovalOrReview.current_reviewer))
            .options(
                joinedload(MouApprovalOrReview.comments).joinedload(MouComment.user)
            )
            .filter(MouApprovalOrReview.mou_application_id == uuid)
            .order_by(MouApprovalOrReview.created_at.desc())
        )
        total_items_query = select(func.count()).select_from(
            approval_or_review_query.subquery()
        )
        total_items = (await db.execute(total_items_query)).scalar_one()

        approval_or_reviews_result = await db.execute(
            approval_or_review_query.offset((page - 1) * page_size).limit(page_size)
        )
        approval_or_reviews = approval_or_reviews_result.unique().scalars().all()

        response_data = []
        for approval_or_review in approval_or_reviews:
            current_reviewer = approval_or_review.current_reviewer

            comments = [
                MouApprovalOrReviewCommentRead(
                    uuid=comment.uuid,
                    content=comment.content,
                    created_at=comment.created_at,
                    created_by=comment.created_by,
                )
                for comment in approval_or_review.comments
            ]

            current_reviewer_read = None
            if current_reviewer:
                current_reviewer_read = UserProfileForApprovalOrReview(
                    uuid=current_reviewer.uuid,
                    first_name=current_reviewer.first_name,
                    last_name=current_reviewer.last_name,
                    email=current_reviewer.email,
                    role=current_reviewer.role,
                    level=current_reviewer.level,
                )

            approval_or_review_read = MouApprovalOrReviewRead(
                uuid=approval_or_review.uuid,
                decision=approval_or_review.decision,
                comment=comments[0].content if comments else None,
                created_at=approval_or_review.created_at,
                current_reviewer=current_reviewer_read,
            )
            response_data.append(approval_or_review_read)

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


@router.get("/{uuid}/modification_comments", response_model=List[MouCommentRead])
async def get_modification_comments(
    uuid: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        # Fetch the MOU application to ensure it exists and the user has access
        query = select(MouApplication).where(MouApplication.uuid == uuid)
        result = await db.execute(query)
        mou_application = result.scalar_one_or_none()

        if not mou_application:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND, detail="MOU application not found"
            )

        # Fetch the comments related to the MOU application when the decision was 'REQUEST_MODIFICATION'
        comments_query = (
            select(MouComment)
            .join(MouApprovalOrReview)
            .where(
                MouComment.mou_application_id == uuid,
                MouApprovalOrReview.mou_application_id == uuid,
                MouApprovalOrReview.decision
                == MouApprovalOrReviewDecision.REQUEST_MODIFICATION,
                MouComment.mou_approval_or_review_id == MouApprovalOrReview.uuid,
            )
        )
        comments_result = await db.execute(comments_query)
        comments = comments_result.scalars().all()

        return comments
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


async def update_related_mou_application(
    entity,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    email_handler: EmailNotificationHandler = Depends(get_email_notification_handler),
):
    if isinstance(entity, Activity):
        mou_details_query = select(MouDetail).where(
            MouDetail.project_id == entity.project.uuid
        )
        mou_details = (await db.execute(mou_details_query)).scalars().all()
    elif isinstance(entity, MouDetail):
        mou_details = [entity] if entity is not None else []
    elif isinstance(entity, Project):
        mou_details_query = select(MouDetail).where(MouDetail.project_id == entity.uuid)
        mou_details = (await db.execute(mou_details_query)).scalars().all()
    elif isinstance(entity, Party):
        mou_detail_query = select(MouDetail).where(
            MouDetail.uuid == entity.mou_detail_id
        )
        mou_details = (await db.execute(mou_detail_query)).scalars().all()
    else:
        return

    if not mou_details or len(mou_details) == 0:
        return

    for mou_detail in mou_details:
        mou_application = mou_detail.mou_application

        if not mou_application:
            application_query = (
                select(MouApplication)
                .where(MouApplication.mou_detail_id == mou_detail.uuid)
                .order_by(MouApplication.created_at.desc())
                .limit(1)
            )
            mou_application = (await db.execute(application_query)).scalar_one_or_none()

        if mou_application:
            mou_application.status = MouApplicationStatus.MODIFIED
            print("JUST MODIFIED THE STATUS OF THE MOU APPLICATION")
            file_path, filename = await generate_mou_action_plan(mou_application, db)

            existing_documents = await db.execute(
                select(Document).where(
                    Document.mou_application_id == mou_application.uuid,
                    Document.document_type == DocumentType.ADDITIONAL_DOCUMENT,
                )
            )
            existing_documents = existing_documents.scalars().all()

            if existing_documents:
                for doc in existing_documents:
                    doc.path = file_path
                    doc.filename = filename
            else:
                new_document = Document(
                    name=f"MOU Application Action Plan - {mou_application.id}",
                    description="Action Plan Report",
                    document_type=DocumentType.ADDITIONAL_DOCUMENT,
                    path=file_path,
                    filename=filename,
                    mou_application=mou_application,
                    created_by=mou_application.created_by,
                )
                db.add(new_document)

            mou_application.last_updated_at = datetime.utcnow()
            mou_application.last_updated_by = mou_application.created_by
            await notify_moh_staff(
                db,
                email_handler,
                levels=[MOHStaffLevel.PARTNER_COORDINATOR],
                subject="MOU Application Modified",
                message=f"An MOU application (ID: {mou_application.id}) has been modified and requires your attention.",
                created_by=mou_application.last_updated_by,
                background_tasks=background_tasks,
            )

            await db.commit()
            await db.refresh(mou_application)
