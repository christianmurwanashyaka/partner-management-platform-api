from datetime import datetime
from typing import List, Optional

import uuid
from fastapi import APIRouter, Request, Depends, status, HTTPException
from sqlalchemy import select, func
from sqlalchemy.orm import joinedload
from sqlmodel.ext.asyncio.session import AsyncSession
from api.dependencies.access_control import partner_access, moh_staff_access
from api.dependencies.auth import get_current_user
from db.database import get_db
from db.models import User, MouDetail, MouApplication, Document, DocumentType, UserRole, MOHStaffLevel, \
    MouApprovalDecision, MouApproval, MouApplicationStatus, MouComment, Project, Mou, MouReview, PaginatedResponse, \
    Organization, Activity, ActivityDomain
from db.models.mou_approval_or_review import MouApprovalOrReview, MouApprovalOrReviewDecision
from db.models.mou_review import MouReviewDecision
from helpers.db import get_first_item
from schemas.activity import ActivityDomainDetail
from schemas.approval_and_review import CombinedApprovalOrReviewRead
from schemas.comment import MouCommentRead
from schemas.mou_application import MouApplicationRead, MouApplicationCreate, SimpleOrganizationRead, \
    MouApplicationOrganizationRead, MouApplicationBasicCommentRead
from schemas.mou_approval import MouApprovalRead, MouApprovalCreate
from schemas.mou_approval_or_review import MouApprovalOrReviewRead, MouApprovalOrReviewCreate, \
    UserProfileForApprovalOrReview, MouApprovalOrReadCommentRead
from schemas.mou_review import MouReviewRead, MouReviewCreate
from schemas.user import UserProfile
from utils.files import generate_mou_action_plan, generate_mou_doc, save_mou_doc_to_disk

router = APIRouter()


@router.post('/', response_model=MouApplicationRead, dependencies=[Depends(partner_access)])
async def create_mou_application(
        request: Request,
        mou_application_data: MouApplicationCreate,
        db: AsyncSession = Depends(get_db)):
    user = request.state.user.email
    try:
        query = select(MouDetail).filter(MouDetail.uuid == mou_application_data.mou_detail_id)

        mou_detail = await get_first_item(db, query)

        if not mou_detail:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Mou detail not found')

        new_mou_application = MouApplication(mou_detail_id=mou_application_data.mou_detail_id, created_by=user)

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
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    try:
        if current_user.role in ['admin', 'moh_staff']:
            query = select(MouApplication).options(
                joinedload(MouApplication.mou_detail).joinedload(MouDetail.project).joinedload(Project.organization),
                joinedload(MouApplication.documents),
                joinedload(MouApplication.mou_detail).joinedload(MouDetail.documents),
                joinedload(MouApplication.mou_detail).joinedload(MouDetail.project).joinedload(Project.activities).joinedload(Activity.domains),
                joinedload(MouApplication.mou_detail).joinedload(MouDetail.project).joinedload(Project.activities).joinedload(Activity.input_details),
                joinedload(MouApplication.mou_detail).joinedload(MouDetail.project).joinedload(Project.organization).joinedload(Organization.documents),
                joinedload(MouApplication.comments).joinedload(MouComment.user),
                joinedload(MouApplication.approvals).joinedload(MouApproval.comments).joinedload(MouComment.user),
                joinedload(MouApplication.reviews).joinedload(MouReview.comments).joinedload(MouComment.user),
                joinedload(MouApplication.current_reviewer)
            ).order_by(MouApplication.created_at.desc())
        elif current_user.role == 'partner':
            query = select(MouApplication).where(MouApplication.created_by == current_user.email).options(
                joinedload(MouApplication.mou_detail).joinedload(MouDetail.project).joinedload(Project.organization),
                joinedload(MouApplication.documents),
                joinedload(MouApplication.mou_detail).joinedload(MouDetail.documents),
                joinedload(MouApplication.mou_detail).joinedload(MouDetail.project).joinedload(Project.activities).joinedload(Activity.domains),
                joinedload(MouApplication.mou_detail).joinedload(MouDetail.project).joinedload(Project.activities).joinedload(Activity.input_details),
                joinedload(MouApplication.mou_detail).joinedload(MouDetail.project).joinedload(Project.organization).joinedload(Organization.documents),
                joinedload(MouApplication.comments).joinedload(MouComment.user),
                joinedload(MouApplication.approvals).joinedload(MouApproval.comments).joinedload(MouComment.user),
                joinedload(MouApplication.reviews).joinedload(MouReview.comments).joinedload(MouComment.user),
                joinedload(MouApplication.current_reviewer)
            ).order_by(MouApplication.created_at.desc())
        else:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail='You are not authorized to perform this action')

        total_items_query = select(func.count()).select_from(query.subquery())
        total_items = (await db.execute(total_items_query)).scalar_one()

        mou_applications_result = await db.execute(query.offset((page - 1) * page_size).limit(page_size))
        mou_applications = mou_applications_result.unique().scalars().all()

        response = []
        for app in mou_applications:
            organization = app.mou_detail.project.organization

            # Collecting all related documents
            all_documents = app.documents + app.mou_detail.documents + organization.documents

            current_reviewer = app.current_reviewer
            if current_reviewer:
                current_reviewer_read = UserProfileForApprovalOrReview(
                    uuid=current_reviewer.uuid,
                    first_name=current_reviewer.first_name,
                    last_name=current_reviewer.last_name,
                    email=current_reviewer.email,
                    role=current_reviewer.role,
                    level=current_reviewer.level
                )
            else:
                current_reviewer_read = None

            app_with_org = MouApplicationOrganizationRead(
                created_at=app.created_at,
                created_by=app.created_by,
                uuid=app.uuid,
                status=app.status,
                mou_detail=app.mou_detail,
                documents=all_documents,
                organization=SimpleOrganizationRead(
                    uuid=organization.uuid,
                    name=organization.name,
                    email=organization.email,
                    website=organization.website
                ),
                current_reviewer=current_reviewer_read,
                next_level=app.next_level
            )
            response.append(app_with_org)

        total_pages = (total_items + page_size - 1) // page_size
        return PaginatedResponse(
            page=page,
            page_size=page_size,
            total_items=total_items,
            total_pages=total_pages,
            data=response
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
                    website=organization.website
                )
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
        mou_application.current_reviewer_id = user.uuid

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
        approval_query = select(MouApproval).filter(MouApproval.mou_application_id == uuid).order_by(MouApproval.created_at.desc())
        total_items_query = select(func.count()).select_from(approval_query.subquery())
        total_items = (await db.execute(total_items_query)).scalar_one()

        approvals_result = await db.execute(approval_query.offset((page - 1) * page_size).limit(page_size))
        approvals = approvals_result.scalars().all()

        total_pages = (total_items + page_size - 1) // page_size
        paginated_response = PaginatedResponse(
            page=page,
            page_size=page_size,
            total_items=total_items,
            total_pages=total_pages,
            data=approvals
        )

        return paginated_response

    except Exception as e:
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
        review_query = select(MouReview).filter(MouReview.mou_application_id == uuid).order_by(MouReview.created_at.desc())
        total_items_query = select(func.count()).select_from(review_query.subquery())
        total_items = (await db.execute(total_items_query)).scalar_one()

        reviews_result = await db.execute(review_query.offset((page - 1) * page_size).limit(page_size))
        reviews = reviews_result.scalars().all()

        total_pages = (total_items + page_size - 1) // page_size
        paginated_response = PaginatedResponse(
            page=page,
            page_size=page_size,
            total_items=total_items,
            total_pages=total_pages,
            data=reviews
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
                MouApprovalOrReadCommentRead(
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


@router.post('/{uuid}/approval_or_review', response_model=MouApprovalOrReviewRead, dependencies=[Depends(moh_staff_access)])
async def add_approval_or_review(
        uuid: uuid.UUID,
        approval_or_review: MouApprovalOrReviewCreate,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    try:
        query = select(MouApplication).where(MouApplication.uuid == uuid)
        result = await db.execute(query)
        mou_application = result.scalar_one_or_none()

        if not mou_application:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail='MOU application not found')

        # Check if the current user is allowed to make the decision
        if current_user.level == MOHStaffLevel.TECHNICAL_DEPARTMENT:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail='Technical department user not allowed to make decisions')

        # Ensure that only the partner coordinator can submit a decision if the application doesn't have a next level
        if not mou_application.next_level and current_user.level != MOHStaffLevel.PARTNER_COORDINATOR:
            raise HTTPException(status.HTTP_403_FORBIDDEN,
                                detail='Only the partner coordinator can submit a decision at this stage')

        # Validate that the current user is at the correct level to submit the decision
        if mou_application.next_level and not ((mou_application.next_level == current_user.level) or (mou_application.next_level in [MOHStaffLevel.MINISTER_OF_STATE, MOHStaffLevel.MINISTER] and current_user.level in [MOHStaffLevel.MINISTER_OF_STATE, MOHStaffLevel.MINISTER])):
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail='You are not authorized to make this decision at this stage')

        # Validate the decision based on the user's level
        allowed_decisions = {
            MOHStaffLevel.PARTNER_COORDINATOR: [
                MouApprovalOrReviewDecision.RECOMMEND_APPROVAL,
                MouApprovalOrReviewDecision.REJECT,
                MouApprovalOrReviewDecision.REQUEST_MODIFICATION
            ],
            MOHStaffLevel.HOD: [
                MouApprovalOrReviewDecision.APPROVE,
                MouApprovalOrReviewDecision.REJECT
            ],
            MOHStaffLevel.LEGAL_ADVISOR: [
                MouApprovalOrReviewDecision.APPROVE,
                MouApprovalOrReviewDecision.REJECT
            ],
            MOHStaffLevel.PS: [
                MouApprovalOrReviewDecision.APPROVE,
                MouApprovalOrReviewDecision.REJECT
            ],
            MOHStaffLevel.MINISTER_OF_STATE: [
                MouApprovalOrReviewDecision.APPROVE,
                MouApprovalOrReviewDecision.REJECT
            ],
            MOHStaffLevel.MINISTER: [
                MouApprovalOrReviewDecision.APPROVE,
                MouApprovalOrReviewDecision.REJECT
            ]
        }

        if approval_or_review.decision not in allowed_decisions.get(current_user.level, []):
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail='You are not authorized to make this decision')

        new_approval_or_review = MouApprovalOrReview(
            mou_application_id=uuid,
            decision=approval_or_review.decision,
            current_reviewer_id=current_user.uuid,
            created_by=current_user.email
        )

        db.add(new_approval_or_review)
        await db.commit()
        await db.refresh(new_approval_or_review)

        comment_content = None
        if approval_or_review.comment:
            new_comment = MouComment(
                content=approval_or_review.comment,
                user_id=current_user.uuid,
                mou_application_id=uuid,
                mou_approval_or_review_id=new_approval_or_review.uuid,
                created_by=current_user.email
            )
            db.add(new_comment)
            await db.commit()
            await db.refresh(new_comment)
            comment_content = new_comment.content

        # Define the flow of levels
        level_flow = [
            MOHStaffLevel.PARTNER_COORDINATOR,
            MOHStaffLevel.HOD,
            MOHStaffLevel.LEGAL_ADVISOR,
            MOHStaffLevel.PS,
            MOHStaffLevel.MINISTER_OF_STATE,
            MOHStaffLevel.MINISTER
        ]

        # Determine the next level based on the current level and decision
        next_level = None

        if current_user.level == MOHStaffLevel.PARTNER_COORDINATOR:
            if approval_or_review.decision == MouApprovalOrReviewDecision.RECOMMEND_APPROVAL:
                mou_application.status = MouApplicationStatus.UNDER_APPROVAL
                next_level = MOHStaffLevel.HOD
            elif approval_or_review.decision == MouApprovalOrReviewDecision.REQUEST_MODIFICATION:
                mou_application.status = MouApplicationStatus.REQUEST_MODIFICATION
                next_level = MOHStaffLevel.PARTNER_COORDINATOR
            elif approval_or_review.decision == MouApprovalOrReviewDecision.REJECT:
                mou_application.status = MouApplicationStatus.REJECTED
                next_level = None

        elif current_user.level in [
            MOHStaffLevel.HOD,
            MOHStaffLevel.LEGAL_ADVISOR,
            MOHStaffLevel.PS
        ]:
            if approval_or_review.decision == MouApprovalOrReviewDecision.APPROVE:
                mou_application.status = MouApplicationStatus.UNDER_APPROVAL
                next_level = level_flow[level_flow.index(current_user.level) + 1]
            elif approval_or_review.decision == MouApprovalOrReviewDecision.REJECT:
                mou_application.status = MouApplicationStatus.UNDER_REVIEW
                next_level = MOHStaffLevel.PARTNER_COORDINATOR

        elif current_user.level in [
            MOHStaffLevel.MINISTER_OF_STATE,
            MOHStaffLevel.MINISTER
        ]:
            if approval_or_review.decision == MouApprovalOrReviewDecision.APPROVE:
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
            elif approval_or_review.decision == MouApprovalOrReviewDecision.REJECT:
                mou_application.status = MouApplicationStatus.REJECTED
                next_level = None

        mou_application.current_reviewer_id = current_user.uuid
        mou_application.next_level = next_level

        await db.commit()
        await db.refresh(mou_application)

        return MouApprovalOrReviewRead(
            uuid=new_approval_or_review.uuid,
            decision=new_approval_or_review.decision,
            comment=comment_content,
            created_at=new_approval_or_review.created_at,
            created_by=new_approval_or_review.created_by,
            current_reviewer=current_user,
            next_level=next_level
        )
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


async def update_related_mou_application(entity, db: AsyncSession = Depends(get_db)):
    if isinstance(entity, Activity):
        mou_details = entity.project.mou_details
    elif isinstance(entity, MouDetail):
        mou_details = [entity]
    elif isinstance(entity, Project):
        mou_details = entity.mou_details
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