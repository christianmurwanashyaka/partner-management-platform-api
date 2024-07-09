import time
from datetime import datetime
from typing import List, Optional

import uuid
from fastapi import APIRouter, Request, Depends, status, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.orm import joinedload, selectinload
from sqlmodel.ext.asyncio.session import AsyncSession
from api.dependencies.access_control import partner_access, moh_staff_access
from api.dependencies.auth import get_current_user
from db.database import get_db
from db.models import User, MouDetail, MouApplication, Document, DocumentType, UserRole, MOHStaffLevel, \
    MouApprovalDecision, MouApproval, MouApplicationStatus, MouComment, Project, Mou, MouReview, PaginatedResponse, \
    Organization, Activity, ActivityDomain, InputDetail, Party
from db.models.mou_approval_or_review import MouApprovalOrReview, MouApprovalOrReviewDecision
from db.models.mou_review import MouReviewDecision
from helpers.db import get_first_item, get_most_recent_decision_time
from schemas.activity import ActivityDomainDetail
from schemas.approval_and_review import CombinedApprovalOrReviewRead
from schemas.comment import MouCommentRead
from schemas.mou_application import MouApplicationRead, MouApplicationCreate, SimpleOrganizationRead, \
    MouApplicationOrganizationRead, MouApplicationBasicCommentRead
from schemas.mou_approval import MouApprovalRead, MouApprovalCreate
from schemas.mou_approval_or_review import MouApprovalOrReviewRead, MouApprovalOrReviewCreate, \
    UserProfileForApprovalOrReview, MouApprovalOrReviewCommentRead
from schemas.mou_review import MouReviewRead, MouReviewCreate
from schemas.user import UserProfile
from utils.files import generate_mou_action_plan, generate_mou_doc, save_mou_doc_to_disk
from utils.filters import parse_uuid_list, parse_string_list
from utils.functions import calculate_time_difference_ms, format_time_difference

router = APIRouter()


@router.post('/', response_model=MouApplicationRead, dependencies=[Depends(partner_access)])
async def create_mou_application(
        request: Request,
        mou_application_data: MouApplicationCreate,
        db: AsyncSession = Depends(get_db)):
    user = request.state.user.email
    full_name = request.state.user.first_name + ' ' + request.state.user.last_name

    try:
        query = select(MouDetail).filter(MouDetail.uuid == mou_application_data.mou_detail_id)

        mou_detail = await get_first_item(db, query)

        if not mou_detail:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Mou detail not found')

        new_mou_application = MouApplication(
            mou_detail_id=mou_application_data.mou_detail_id,
            created_by=user,
            submitted_by=full_name
        )

        db.add(new_mou_application)
        await db.commit()
        await db.refresh(new_mou_application)

        file_path, filename = await generate_mou_action_plan(new_mou_application, db)

        excel_document = Document(
            name=f"MOU Application Action Plan - {new_mou_application.id}",
            description='Action Plan Report',
            document_type=DocumentType.ADDITIONAL_DOCUMENT,
            path=file_path,
            filename=filename,
            mou_application=new_mou_application,
            created_by=user
        )

        db.add(excel_document)
        await db.commit()
        await db.refresh(excel_document)

        return new_mou_application

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get('/', response_model=PaginatedResponse[MouApplicationOrganizationRead])
async def get_mou_applications(
        page: int = 1,
        page_size: int = 100,
        organization_uuids: Optional[List[str]] = Query(None),
        funding_source_uuids: Optional[List[str]] = Query(None),
        funding_unit_uuids: Optional[List[str]] = Query(None),
        budget_type_uuids: Optional[List[str]] = Query(None),
        domain_intervention_uuids: Optional[List[str]] = Query(None),
        sub_domain_uuids: Optional[List[str]] = Query(None),
        sub_domain_function_uuids: Optional[List[str]] = Query(None),
        sub_function_uuids: Optional[List[str]] = Query(None),
        input_category_uuids: Optional[List[str]] = Query(None),
        input_uuids: Optional[List[str]] = Query(None),
        districts: Optional[List[str]] = Query(None),
        provinces: Optional[List[str]] = Query(None),
        application_status: Optional[List[str]] = Query(None),
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    try:

        # Parse URL-encoded, comma-separated UUIDs
        organization_uuids = parse_uuid_list(organization_uuids)
        funding_source_uuids = parse_uuid_list(funding_source_uuids)
        funding_unit_uuids = parse_uuid_list(funding_unit_uuids)
        budget_type_uuids = parse_uuid_list(budget_type_uuids)
        domain_intervention_uuids = parse_uuid_list(domain_intervention_uuids)
        sub_domain_uuids = parse_uuid_list(sub_domain_uuids)
        sub_domain_function_uuids = parse_uuid_list(sub_domain_function_uuids)
        sub_function_uuids = parse_uuid_list(sub_function_uuids)
        input_category_uuids = parse_uuid_list(input_uuids)
        input_uuids = parse_uuid_list(input_uuids)

        # Parse URL-encoded, comma-separated strings
        districts = parse_string_list(districts)
        provinces = parse_string_list(provinces)
        application_status = parse_string_list(application_status)


        query = (
            select(
                MouApplication.created_at,
                MouApplication.submitted_by,
                MouApplication.uuid,
                MouApplication.status,
                MouApplication.next_level,
                Organization.name.label('organization')
            )
            .join(MouApplication.mou_detail)
            .join(MouDetail.project)
            .join(Project.organization)
            .order_by(MouApplication.created_at.desc())
        )

        if current_user.role == 'partner':
            query = query.filter(MouApplication.created_by == current_user.email)

        # Filtering by organization uuids
        if organization_uuids:
            query = query.filter(Project.organization_id.in_(organization_uuids))

        # Filtering by funding source uuids
        if funding_source_uuids:
            query = query.filter(Project.funding_source_id.in_(funding_source_uuids))

        # Filtering by funding unit uuids
        if funding_unit_uuids:
            query = query.filter(Project.funding_unit_id.in_(funding_unit_uuids))

        # Filtering by budget type uuids
        if budget_type_uuids:
            query = query.filter(Project.budget_type_id.in_(budget_type_uuids))

        # Filtering by domain intervention uuids
        if domain_intervention_uuids:
            query = query.filter(ActivityDomain.domain_intervention_id.in_(domain_intervention_uuids))

        # Filtering by subdomain uuids
        if sub_domain_uuids:
            query = query.filter(ActivityDomain.sub_domain_id.in_(sub_domain_uuids))

        # Filtering by subdomain function uuids
        if sub_domain_function_uuids:
            query = query.filter(ActivityDomain.sub_domain_function_id.in_(sub_domain_function_uuids))

        if sub_function_uuids:
            query = query.filter(ActivityDomain.sub_function_id.in_(sub_function_uuids))

        # Filtering by input category uuids
        if input_category_uuids:
            query = query.filter(InputDetail.input_category_id.in_(input_category_uuids))

        # Filtering by input uuids
        if input_uuids:
            query = query.filter(InputDetail.input_id.in_(input_uuids))

        # Filtering by districts
        if districts:
            query = query.filter(InputDetail.district.in_(districts))

        # Filtering by provinces
        if provinces:
            query = query.filter(InputDetail.province.in_(provinces))

        # filter by status
        if application_status:
            query = query.filter(MouApplication.status.in_(application_status))

        count_query = select(func.count()).select_from(query.subquery())
        total_items = (await db.execute(count_query)).scalar_one()

        mou_applications_result = await db.execute(query.offset((page - 1) * page_size).limit(page_size))
        mou_applications = mou_applications_result.all()

        response_data = [
            MouApplicationOrganizationRead(
                created_at=app.created_at,
                submitted_by=app.submitted_by,
                reference_number=f"{app.created_at:%Y%m%d}-{app.uuid.int % 1000000:06d}",
                uuid=app.uuid,
                status=app.status,
                organization=app.organization,
                next_level=app.next_level
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

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get('/{uuid}', response_model=MouApplicationRead)
async def get_mou_application(
        uuid: uuid.UUID,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    try:
        query = select(MouApplication).filter(MouApplication.uuid == uuid).options(
            joinedload(MouApplication.mou_detail).joinedload(MouDetail.project).joinedload(Project.organization),
            joinedload(MouApplication.documents),
            joinedload(MouApplication.mou_detail).joinedload(MouDetail.documents),
            joinedload(MouApplication.mou_detail).joinedload(MouDetail.project).joinedload(Project.activities).joinedload(Activity.domains),
            joinedload(MouApplication.mou_detail).joinedload(MouDetail.project).joinedload(Project.activities).joinedload(Activity.input_details),
            joinedload(MouApplication.mou_detail).joinedload(MouDetail.project).joinedload(Project.organization).joinedload(Organization.documents),
            joinedload(MouApplication.comments).joinedload(MouComment.user),
            joinedload(MouApplication.approvals).joinedload(MouApproval.comments).joinedload(MouComment.user),
            joinedload(MouApplication.reviews).joinedload(MouReview.comments).joinedload(MouComment.user)
        )
        mou_application_result = await db.execute(query)
        mou_application = mou_application_result.unique().scalar_one_or_none()

        if not mou_application:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail='MOU application not found')

        if current_user.role in ['admin', 'moh_staff'] or (current_user.role == 'partner' and mou_application.created_by == current_user.email):
            organization = mou_application.mou_detail.project.organization

            # Collecting all related documents
            all_documents = mou_application.documents + mou_application.mou_detail.documents + organization.documents

            mou_application_with_documents = MouApplicationRead(
                uuid=mou_application.uuid,
                status=mou_application.status,
                mou_detail=mou_application.mou_detail,
                documents=all_documents,  # Adding all related documents
                organization=SimpleOrganizationRead(
                    uuid=organization.uuid,
                    name=organization.name,
                    email=organization.email,
                    website=organization.website,
                    organization_type=organization.organization_type.name,
                ),
                comments=mou_application.comments,
                submitted_by=mou_application.submitted_by,
                modification_entity=mou_application.modification_entity,
                last_decision_date=mou_application.last_decision_date
            )

            return mou_application_with_documents
        else:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail='You are not authorized to access this MOU application')

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.patch('/{uuid}/start_review', response_model=MouApplicationRead, dependencies=[Depends(moh_staff_access)])
async def start_review(uuid: str, request: Request, db: AsyncSession = Depends(get_db)):
    user = request.state.user
    if user.role != UserRole.MOH_STAFF or user.level != MOHStaffLevel.PARTNER_COORDINATOR:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='You are not authorized to perform this action')

    try:
        query = select(MouApplication).filter(MouApplication.uuid == uuid)
        mou_application = await get_first_item(db, query)

        if not mou_application:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='MOU application not found')

        if mou_application.status != MouApplicationStatus.PENDING:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='MOU application is not in a pending state')

        mou_application.status = MouApplicationStatus.UNDER_REVIEW
        mou_application.last_decision_date = datetime.now()
        mou_application.last_updated_at = datetime.now()

        await db.commit()
        await db.refresh(mou_application)

        return mou_application
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get('/{uuid}/approvals', response_model=PaginatedResponse[MouApprovalRead])
async def get_mou_application_approvals(
        uuid: str,
        page: int = 1,
        page_size: int = 100,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    try:
        # Check if the MOU application exists
        query = select(MouApplication).filter(MouApplication.uuid == uuid)
        mou_application_result = await db.execute(query)
        mou_application = mou_application_result.scalar_one_or_none()

        if not mou_application:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail='MOU application not found')

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

        approvals_result = await db.execute(approval_query.offset((page - 1) * page_size).limit(page_size))
        approvals = approvals_result.scalars().unique().all()

        response_data = []

        for approval in approvals:
            current_approver = approval.current_approver
            comments = [MouApprovalOrReviewCommentRead(uuid=comment.uuid, content=comment.content, created_at=comment.created_at, created_by=comment.created_by) for comment in approval.comments]

            current_approver_read = None
            if current_approver:
                current_approver_read = UserProfileForApprovalOrReview(uuid=current_approver.uuid, first_name=current_approver.first_name, last_name=current_approver.last_name, email=current_approver.email, role=current_approver.role, level=current_approver.level)

            processing_time_dict = format_time_difference(approval.processing_time)

            approval_read = MouApprovalRead(uuid=approval.uuid, decision=approval.decision, comment=comments[0].content if comments else None, created_at=approval.created_at, current_approver=current_approver_read, processing_time=processing_time_dict)

            response_data.append(approval_read)

        total_pages = (total_items + page_size - 1) // page_size
        paginated_response = PaginatedResponse(
            page=page,
            page_size=page_size,
            total_items=total_items,
            total_pages=total_pages,
            data=response_data
        )

        return paginated_response

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post('/{uuid}/review', response_model=MouReviewRead, dependencies=[Depends(moh_staff_access)])
async def add_review(
        uuid: uuid.UUID,
        review: MouReviewCreate,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    try:
        query = select(MouApplication).where(MouApplication.uuid == uuid)
        result = await db.execute(query)
        mou_application = result.scalar_one_or_none()

        if not mou_application:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail='MOU application not found')

        # Initial review checks
        if mou_application.next_level is None:
            # New application
            if current_user.level not in [MOHStaffLevel.TECHNICAL_DEPARTMENT, MOHStaffLevel.LEGAL_ADVISOR]:
                raise HTTPException(status.HTTP_403_FORBIDDEN,
                                    detail='Only technical department or legal advisor can review a new application')

            # Handle initial reviews
            if review.decision == MouReviewDecision.REJECT:
                raise HTTPException(
                    status.HTTP_403_FORBIDDEN,
                    detail='Only partner coordinator is allowed to reject an application in the review stage'
                )
            if review.decision == MouReviewDecision.VERIFIED:
                next_level = MOHStaffLevel.LEGAL_ADVISOR if current_user.level == MOHStaffLevel.TECHNICAL_DEPARTMENT else MOHStaffLevel.TECHNICAL_DEPARTMENT
            elif review.decision == MouReviewDecision.REQUEST_MODIFICATION:
                next_level = MOHStaffLevel.PARTNER_COORDINATOR
            else:
                raise HTTPException(status.HTTP_403_FORBIDDEN, detail='Invalid decision for the initial review')

        else:
            # Application with reviews
            if current_user.level != mou_application.next_level:
                raise HTTPException(status.HTTP_403_FORBIDDEN,
                                    detail='You are not authorized to make decisions at this level')

            if current_user.level == MOHStaffLevel.PARTNER_COORDINATOR:
                if review.decision == MouReviewDecision.RECOMMEND_APPROVAL:
                    mou_application.status = MouApplicationStatus.UNDER_APPROVAL
                    next_level = MOHStaffLevel.HOD
                elif review.decision == MouReviewDecision.REQUEST_MODIFICATION:
                    mou_application.status = MouApplicationStatus.REQUEST_MODIFICATION
                    if review.modification_entity:
                        mou_application.modification_entity = review.modification_entity  # Store the list directly
                    # Ensure next level is not stuck at partner coordinator
                        next_level = MOHStaffLevel.PARTNER_COORDINATOR
                elif review.decision == MouReviewDecision.REJECT:
                    mou_application.status = MouApplicationStatus.REJECTED
                    next_level = None
                else:
                    raise HTTPException(status.HTTP_403_FORBIDDEN, detail='Invalid decision for partner coordinator')

            elif current_user.level in [MOHStaffLevel.TECHNICAL_DEPARTMENT, MOHStaffLevel.LEGAL_ADVISOR]:
                if review.decision == MouReviewDecision.VERIFIED:
                    if not mou_application.next_level:  # Only set next_level if it is currently null
                        next_level = MOHStaffLevel.LEGAL_ADVISOR if current_user.level == MOHStaffLevel.TECHNICAL_DEPARTMENT else MOHStaffLevel.TECHNICAL_DEPARTMENT
                    else:
                        next_level = MOHStaffLevel.PARTNER_COORDINATOR
                elif review.decision == MouReviewDecision.REQUEST_MODIFICATION:
                    next_level = MOHStaffLevel.PARTNER_COORDINATOR
                else:
                    raise HTTPException(status.HTTP_403_FORBIDDEN,
                                        detail='Invalid decision for technical department or legal advisor')

        previous_decision_time = await get_most_recent_decision_time(db, uuid)
        processing_time_ms = calculate_time_difference_ms(previous_decision_time, datetime.now())

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
                created_by=current_user.email
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
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post('/{uuid}/approval', response_model=MouApprovalRead, dependencies=[Depends(moh_staff_access)])
async def add_approval(
        uuid: uuid.UUID,
        approval: MouApprovalCreate,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    try:
        query = select(MouApplication).where(MouApplication.uuid == uuid)
        result = await db.execute(query)
        mou_application = result.scalar_one_or_none()

        if not mou_application:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail='MOU application not found')

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
            MOHStaffLevel.MINISTER
            # MOHStaffLevel.MINISTER_OF_STATE,
        ]

        # Check if the current user is allowed to make the decision
        if current_user.level not in approval_stage_levels:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail='You are not authorized to make decisions in the approval stage')

        if approval.decision not in approval_stage_decisions:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail='Invalid decision for the approval stage')

        # TODO: ADD VALIDATION TO MAKE SURE THE PERSON MAKING THE DECISON IS TRULY THE ONE THAT SHOULD BE MAKING THE DECISION AT THAT STAGE

        # Handle decisions in the approval stage
        if approval.decision == MouApprovalDecision.APPROVE:
            if current_user.level == MOHStaffLevel.MINISTER:
                mou_application.status = MouApplicationStatus.APPROVED
                organization = mou_application.mou_detail.project.organization
                template_path = 'mou_templates/mou_international.docx' if organization.organization_type.name.lower() == 'international ngo' else 'mou_templates/mou_local.docx'
                document_buffer = await generate_mou_doc(mou_application, template_path)
                filename = f"MOU_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"
                filepath, filename = await save_mou_doc_to_disk(document_buffer, filename)

                new_document = Document(
                    name=f"MOU Application - {mou_application.id}",
                    description="Memorandum of understanding document",
                    document_type=DocumentType.MOU,
                    path=filepath,
                    filename=filename,
                    mou_application_id=uuid,
                    created_by=current_user.email
                )

                db.add(new_document)
                await db.commit()
                await db.refresh(new_document)

                new_mou = Mou(
                    mou_application_id=uuid,
                    mou_detail_id=mou_application.mou_detail_id,
                    document_id=new_document.uuid,
                    created_by=current_user.email
                )

                db.add(new_mou)
                await db.commit()
                await db.refresh(new_mou)
            else:
                next_level_index = approval_stage_levels.index(current_user.level) + 1
                mou_application.next_level = approval_stage_levels[next_level_index]
        elif approval.decision in [MouApprovalDecision.REQUEST_MODIFICATION, MouApprovalDecision.REJECT]:
                mou_application.status = MouApplicationStatus.UNDER_REVIEW
                mou_application.next_level = MOHStaffLevel.PARTNER_COORDINATOR

        # Record the approval
        previous_decision_time = await get_most_recent_decision_time(db, uuid)
        processing_time_ms = calculate_time_difference_ms(previous_decision_time, datetime.now())

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
                created_by=current_user.email
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
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get('/{uuid}/reviews', response_model=PaginatedResponse[MouReviewRead])
async def get_mou_application_reviews(
        uuid: uuid.UUID,
        page: int = 1,
        page_size: int = 100,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    try:
        # Check if the MOU application exists
        query = select(MouApplication).filter(MouApplication.uuid == uuid)
        mou_application_result = await db.execute(query)
        mou_application = mou_application_result.scalar_one_or_none()

        if not mou_application:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail='MOU application not found')

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
                    created_by=comment.created_by
                )
                for comment in review.comments
            ]

            current_reviewer_read = None
            if current_reviewer:
                print('CURRENT REVIEWER :::::::::::::', current_reviewer)
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
                processing_time=processing_time_dict)

            response_data.append(review_read)

        total_pages = (total_items + page_size - 1) // page_size
        paginated_response = PaginatedResponse(
            page=page,
            page_size=page_size,
            total_items=total_items,
            total_pages=total_pages,
            data=response_data
        )

        return paginated_response

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get('/{uuid}/comments', response_model=List[MouCommentRead])
async def get_application_comments(
        uuid: uuid.UUID,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    try:
        # Fetch the MOU application to ensure it exists and the user has access
        query = select(MouApplication).where(MouApplication.uuid == uuid)
        result = await db.execute(query)
        mou_application = result.scalar_one_or_none()

        if not mou_application:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail='MOU application not found')

        if current_user.role not in ['admin', 'moh_staff'] and mou_application.created_by != current_user.email:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail='You are not authorized to access this MOU application')

        # Fetch the comments related to the MOU application
        comments_query = select(MouComment).where(MouComment.mou_application_id == uuid)
        comments_result = await db.execute(comments_query)
        comments = comments_result.scalars().all()

        return comments
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get('/{uuid}/approval_or_review', response_model=PaginatedResponse[MouApprovalOrReviewRead])
async def get_mou_application_approvals_or_reviews(
        uuid: uuid.UUID,
        page: int = 1,
        page_size: int = 100,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    try:
        # Check if the MOU application exists
        query = select(MouApplication).filter(MouApplication.uuid == uuid)
        mou_application_result = await db.execute(query)
        mou_application = mou_application_result.scalar_one_or_none()

        if not mou_application:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail='MOU application not found')

        # Query to get approvals or reviews with eager loading of current_reviewer and comments
        approval_or_review_query = (
            select(MouApprovalOrReview)
            .options(joinedload(MouApprovalOrReview.current_reviewer))
            .options(joinedload(MouApprovalOrReview.comments).joinedload(MouComment.user))
            .filter(MouApprovalOrReview.mou_application_id == uuid)
            .order_by(MouApprovalOrReview.created_at.desc())
        )
        total_items_query = select(func.count()).select_from(approval_or_review_query.subquery())
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
                    created_by=comment.created_by
                )
                for comment in approval_or_review.comments
            ]

            current_reviewer_read = None
            if current_reviewer:
                print('CURRENT REVIEWER :::::::::::::::::', current_reviewer)
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
                current_reviewer=current_reviewer_read
            )
            response_data.append(approval_or_review_read)

        total_pages = (total_items + page_size - 1) // page_size
        paginated_response = PaginatedResponse(
            page=page,
            page_size=page_size,
            total_items=total_items,
            total_pages=total_pages,
            data=response_data
        )

        return paginated_response

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get('/{uuid}/modification_comments', response_model=List[MouCommentRead])
async def get_modification_comments(
        uuid: uuid.UUID,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    try:
        # Fetch the MOU application to ensure it exists and the user has access
        query = select(MouApplication).where(MouApplication.uuid == uuid)
        result = await db.execute(query)
        mou_application = result.scalar_one_or_none()

        if not mou_application:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail='MOU application not found')

        # Fetch the comments related to the MOU application when the decision was 'REQUEST_MODIFICATION'
        comments_query = select(MouComment).join(MouApprovalOrReview).where(
            MouComment.mou_application_id == uuid,
            MouApprovalOrReview.mou_application_id == uuid,
            MouApprovalOrReview.decision == MouApprovalOrReviewDecision.REQUEST_MODIFICATION,
            MouComment.mou_approval_or_review_id == MouApprovalOrReview.uuid
        )
        comments_result = await db.execute(comments_query)
        comments = comments_result.scalars().all()

        return comments
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


async def update_related_mou_application(entity, db: AsyncSession = Depends(get_db)):
    if isinstance(entity, Activity):
        mou_details = entity.project.mou_details
    elif isinstance(entity, MouDetail):
        mou_details = [entity]
    elif isinstance(entity, Project):
        mou_details = entity.mou_details
    elif isinstance(entity, Party):
        print('IS INSTANCE OF PARTY ::::::::;;')
        mou_details = [entity.mou_detail]
        print('MOU DETAILS :::::::::::', mou_details)
    else:
        return

    print('************************* CHECKING MOU DETAILS *************************')
    for mou_detail in mou_details:
        print('********************** MOU DETAIL **********************')
        mou_application = mou_detail.mou_application
        print('********************** MOU APPLICATION **********************')
        print(mou_application)
        if mou_application:
            print('^^^^^^^^^^^^^^^^^ IF IS TRUE ^^^^^^^^^^^^^^^^^')
            mou_application.status = MouApplicationStatus.MODIFIED
            print('MOU APPLICATION STATUS', mou_application.status)
            file_path, filename = await generate_mou_action_plan(mou_application, db)
            print('FILE PATH ::::::::::::::::::::', file_path)
            print('FILE NAME ::::::::::::::::::::', filename)
            existing_document = await db.execute(
                select(Document).where(
                    Document.mou_application_id == mou_application.uuid,
                    Document.document_type == DocumentType.ADDITIONAL_DOCUMENT
                )
            )
            existing_document = existing_document.scalar_one_or_none()

            if existing_document:
                existing_document.path = file_path
                existing_document.filename = filename
            else:
                new_document = Document(
                    name=f"MOU Application Action Plan - {mou_application.id}",
                    description='Action Plan Report',
                    document_type=DocumentType.ADDITIONAL_DOCUMENT,
                    path=file_path,
                    filename=filename,
                    mou_application=mou_application,
                    created_by=mou_application.created_by
                )
                db.add(new_document)

            mou_application.last_updated_at = datetime.utcnow()
            mou_application.last_updated_by = mou_application.created_by

            await db.commit()
            await db.refresh(mou_application)