from datetime import datetime
from typing import List

from fastapi import APIRouter, Request, Depends, status, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from sqlmodel.ext.asyncio.session import AsyncSession

from api.dependencies.access_control import partner_access, swapteam_member_access
from api.dependencies.auth import get_current_user
from db.database import get_db
from db.models import User, MouDetail, MouApplication, Document, DocumentType, UserRole, SwapTeamLevel, \
    MouApprovalDecision, MouApproval, MouApplicationStatus, MouComment, Project, Mou
from helpers.db import get_first_item
from schemas.mou_application import MouApplicationRead, MouApplicationCreate, SimpleOrganizationRead, \
    MouApplicationOrganizationRead
from schemas.mou_approval import MouApprovalRead, MouApprovalCreate
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


# TODO: UPDATE TO ADD PAGINATION
@router.get('/', response_model=List[MouApplicationOrganizationRead])
async def get_mou_applications(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        if current_user.role in ['admin', 'swapteam_member']:
            query = select(MouApplication)
        elif current_user.role == 'partner':
            query = select(MouApplication).filter(MouApplication.created_by == current_user.email)
        else:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail='You are not authorized to perform this action')

        mou_applications = await db.execute(query)
        mou_applications = mou_applications.scalars().all()

        response = []
        for app in mou_applications:
            organization = app.mou_detail.project.organization
            app_with_org = MouApplicationOrganizationRead(
                uuid=app.uuid,
                status=app.status,
                mou_detail=app.mou_detail,
                documents=app.documents,
                organization=SimpleOrganizationRead(
                    uuid=organization.uuid,
                    name=organization.name,
                    email=organization.email,
                    website=organization.website
                )
            )
            response.append(app_with_org)

        return response

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get('/{uuid}', response_model=MouApplicationRead)
async def get_mou_application(uuid: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        query = select(MouApplication).filter(MouApplication.uuid == uuid)
        mou_application = await db.execute(query)
        mou_application = mou_application.scalar_one_or_none()

        if not mou_application:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail='MOU application not found')

        if current_user.role in ['admin', 'swapteam_member']:
            return mou_application
        elif current_user.role == 'partner' and mou_application.created_by == current_user.email:
            return mou_application
        else:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail='You are not authorized to access this MOU application')

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post('/{uuid}/decision', response_model=MouApprovalRead, dependencies=[Depends(swapteam_member_access)])
async def add_approval_decision(uuid: str, request: Request, approval_data: MouApprovalCreate, db: AsyncSession = Depends(get_db)):
    user = request.state.user

    if user.role != UserRole.SWAPTEAM_MEMBER:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Only swap team members are allowed to make approval decisions')

    try:
        query = select(MouApplication).options(joinedload(MouApplication.mou_detail).joinedload(MouDetail.project).joinedload(Project.organization)).filter(MouApplication.uuid == uuid)
        mou_application = await db.execute(query)
        mou_application = mou_application.scalar_one_or_none()

        if not mou_application:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail='MOU application not found')

        if user.level == SwapTeamLevel.PARTNER_COORDINATOR:
            if approval_data.decision not in [MouApprovalDecision.RECOMMEND_APPROVAL, MouApprovalDecision.RECOMMEND_REJECTION]:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Invalid decision for Partner Coordinator')
        elif user.level == SwapTeamLevel.TECHNICAL_DEPARTMENT:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Technical Department cannot make approval decisions')
        elif user.level in [SwapTeamLevel.LEGAL_ADVISOR, SwapTeamLevel.HOD, SwapTeamLevel.PS]:
            if approval_data.decision not in [MouApprovalDecision.RECOMMEND_APPROVAL, MouApprovalDecision.RECOMMEND_REJECTION, MouApprovalDecision.REQUEST_MODIFICATION]:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f'{user.level} can only recommend for approval, recommend for rejection, or request modification')
        elif user.level in [SwapTeamLevel.MINISTER_OF_STATE, SwapTeamLevel.MINISTER]:
            if approval_data.decision not in [MouApprovalDecision.APPROVE, MouApprovalDecision.REJECT]:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f'{user.level} can only approve or reject')
        new_approval = MouApproval(decision=approval_data.decision, approver_id=user.uuid, approver=user, mou_application_id=uuid, created_by=user.email)

        db.add(new_approval)
        await db.commit()
        await db.refresh(new_approval)

        if approval_data.comment:
            new_comment = MouComment(content=approval_data.comment, user_id=user.uuid, mou_application_id=uuid, mou_approval_id=new_approval.uuid, created_by=user.email)
            db.add(new_comment)
            await db.commit()
            await db.refresh(new_comment)

        if approval_data.decision == MouApprovalDecision.APPROVE:
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
                created_by=user.email
            )

            db.add(new_document)
            await db.commit()
            await db.refresh(new_document)

            new_mou = Mou(
                mou_application_id=uuid,
                mou_detail_id=mou_application.mou_detail_id,
                document_id=new_document.uuid,
                created_by=user.email
            )

            db.add(new_mou)
            await db.commit()
            await db.refresh(new_mou)

        elif approval_data.decision == MouApprovalDecision.REJECT:
            mou_application.status = MouApplicationStatus.REJECTED
        elif approval_data.decision in [MouApprovalDecision.RECOMMEND_APPROVAL, MouApprovalDecision.RECOMMEND_REJECTION, MouApprovalDecision.REQUEST_MODIFICATION]:
            mou_application.status = MouApplicationStatus.UNDER_REVIEW

        await db.commit()
        await db.refresh(mou_application)

        return new_approval

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.patch('/{uuid}/start_review', response_model=MouApplicationRead, dependencies=[Depends(swapteam_member_access)])
async def start_review(uuid: str, request: Request, db: AsyncSession = Depends(get_db)):
    user = request.state.user
    if user.role != UserRole.SWAPTEAM_MEMBER:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='You are not authorized to perform this action')

    try:
        query = select(MouApplication).filter(MouApplication.uuid == uuid)
        mou_application = await get_first_item(db, query)

        if not mou_application:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='MOU application not found')

        mou_application.status = MouApplicationStatus.UNDER_REVIEW
        await db.commit()
        await db.refresh(mou_application)

        return mou_application
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
