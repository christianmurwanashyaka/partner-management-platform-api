from typing import List, Optional

import uuid
from fastapi import APIRouter, Depends, Request, HTTPException, status, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlmodel import select

from api.dependencies.access_control import partner_access
from api.dependencies.auth import get_current_user
from api.dependencies.email_notification_handler import get_email_notification_handler
from api.endpoints.mou_application import update_related_mou_application
from db.database import get_db
from db.models import Party, MouDetail, DocumentType, Document, User, UserRole, Project
from notification.handlers import EmailNotificationHandler
from schemas.mou_detail import MouDetailRead
from utils.files import handle_upload_file
from utils.functions import parse_uuids

router = APIRouter()


@router.post('/', response_model=MouDetailRead, dependencies=[Depends(partner_access)])
async def create_mou_detail(
        request: Request,
        project_id: uuid.UUID = Form(...),
        party_ids: str = Form(...),
        db: AsyncSession = Depends(get_db),
        memo_describing_the_source_of_funds: UploadFile = File(...),
        capacity_building_transfer_plan: UploadFile = File(...),
        memo_describing_the_long_term_objective: UploadFile = File(...),
        strategic_plan: UploadFile = File(...)
):
    user = request.state.user.email
    party_ids = parse_uuids(party_ids)

    try:
        parties = await db.execute(select(Party).where(Party.uuid.in_(party_ids)))
        parties = parties.scalars().all()

        new_mou_detail = MouDetail(
            project_id=project_id,
            created_by=user
        )
        db.add(new_mou_detail)
        await db.commit()

        for party in parties:
            party.mou_detail_id = new_mou_detail.uuid

        async def upload_document(upload_file: UploadFile, document_type: DocumentType):
            if upload_file:
                file_path, filename = await handle_upload_file(upload_file)
                document = Document(
                    name=filename,
                    document_type=document_type,
                    path=file_path,
                    filename=filename,
                    mou_detail=new_mou_detail,
                    created_by=user
                )
                db.add(document)

        await upload_document(memo_describing_the_source_of_funds, DocumentType.MEMO_DESCRIBING_THE_SOURCE_OF_FUNDS)
        await upload_document(capacity_building_transfer_plan, DocumentType.CAPACITY_BUILDING_TRANSFER_PLAN)
        await upload_document(memo_describing_the_long_term_objective, DocumentType.MEMO_DESCRIBING_THE_LONG_TERM_OBJECTIVES)
        await upload_document(strategic_plan, DocumentType.STRATEGIC_PLAN)

        await db.commit()
        await db.refresh(new_mou_detail)

    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

    return new_mou_detail


@router.patch('/{uuid}', response_model=MouDetailRead, dependencies=[Depends(partner_access)])
async def update_mou_detail(
        uuid: uuid.UUID,
        project_id: Optional[uuid.UUID] = Form(None),
        party_ids: Optional[str] = Form(None),
        memo_describing_the_source_of_funds: UploadFile = None,
        capacity_building_transfer_plan: UploadFile = None,
        memo_describing_the_long_term_objective: UploadFile = None,
        strategic_plan: UploadFile = None,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user),
        email_handler: EmailNotificationHandler = Depends(get_email_notification_handler)
):
    try:
        query = select(MouDetail).where(MouDetail.uuid == uuid)
        result = await db.execute(query)
        mou_detail = result.scalar_one_or_none()

        if not mou_detail:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail='MouDetail not found')

        if mou_detail.created_by != current_user.email and current_user.role != UserRole.ADMIN:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail='Not authorized to update this MouDetail')

        # Update the MouDetail fields
        if project_id is not None:
            mou_detail.project_id = project_id

        # Update parties if provided
        if party_ids is not None:
            party_ids_list = parse_uuids(party_ids)
            parties = await db.execute(select(Party).where(Party.uuid.in_(party_ids_list)))
            parties = parties.scalars().all()
            for party in parties:
                party.mou_detail_id = mou_detail.uuid

        async def upload_document(upload_file: Optional[UploadFile], document_type: DocumentType):
            if upload_file:
                # Check if a document of the same type exists
                existing_doc_query = select(Document).where(
                    Document.mou_detail_id == mou_detail.uuid,
                    Document.document_type == document_type
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
                    mou_detail=mou_detail,
                    created_by=current_user.email
                )
                db.add(document)

        await upload_document(memo_describing_the_source_of_funds, DocumentType.MEMO_DESCRIBING_THE_SOURCE_OF_FUNDS)
        await upload_document(capacity_building_transfer_plan, DocumentType.CAPACITY_BUILDING_TRANSFER_PLAN)
        await upload_document(memo_describing_the_long_term_objective, DocumentType.MEMO_DESCRIBING_THE_LONG_TERM_OBJECTIVES)
        await upload_document(strategic_plan, DocumentType.STRATEGIC_PLAN)

        await db.commit()
        await db.refresh(mou_detail)

        await update_related_mou_application(mou_detail, db, email_handler)
        return mou_detail
    except Exception as e:
        await db.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get('/', response_model=List[MouDetailRead])
async def get_mou_details(request: Request, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        if current_user.role in ['admin', 'moh_staff']:
            query = select(MouDetail).options(
                selectinload(MouDetail.project).selectinload(Project.funding_unit),
                selectinload(MouDetail.project).selectinload(Project.budget_type),
                selectinload(MouDetail.documents),
                selectinload(MouDetail.parties)
            )
        elif current_user.role == 'partner':
            query = select(MouDetail).options(
                selectinload(MouDetail.project),
                selectinload(MouDetail.documents),
                selectinload(MouDetail.parties)
            ).where(MouDetail.created_by == current_user.email)
        else:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail='You are not authorized to perform this action')

        mou_details = await db.execute(query)
        mou_details = mou_details.scalars().all()

        return mou_details

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get('/{uuid}', response_model=MouDetailRead)
async def get_mou_detail(uuid: uuid.UUID, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        query = select(MouDetail).options(selectinload(MouDetail.project)).filter(MouDetail.uuid == uuid)
        mou_detail = await db.execute(query)
        mou_detail = mou_detail.scalar_one_or_none()

        if not mou_detail:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail='MOU detail not found')

        if current_user.role in ['admin', 'moh_staff']:
            return mou_detail
        elif current_user.role == 'partner' and mou_detail.created_by == current_user.email:
            return mou_detail
        else:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail='You are not authorized to access this MOU detail')

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
