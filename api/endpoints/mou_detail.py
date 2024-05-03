from typing import List

import uuid
from fastapi import APIRouter, Depends, Request, HTTPException, status, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from api.dependencies.access_control import partner_access
from db.database import get_db
from db.models import Party, MouDetail, DocumentType, Document
from schemas.mou_detail import MouDetailRead
from utils.files import handle_upload_file

router = APIRouter()


@router.post('/', response_model=MouDetailRead, dependencies=[Depends(partner_access)])
async def create_mou_detail(request: Request, project_id: uuid.UUID = Form(...),
                            party_ids: List[uuid.UUID] = Form(...), db: AsyncSession = Depends(get_db),
                            memo_describing_the_source_of_funds: UploadFile = File(...),
                            capacity_building_transfer_plan: UploadFile = File(...),
                            memo_describing_the_long_term_objective: UploadFile = File(...),
                            strategic_plan: UploadFile = File(...)):
    user = request.state.user.email

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


@router.get('/', response_model=List[MouDetailRead], dependencies=[Depends(partner_access)])
async def get_user_mou_details(request: Request, db: AsyncSession = Depends(get_db)):
    user = request.state.user.email

    try:
        mou_details = await db.execute(select(MouDetail).where(MouDetail.created_by == user))
        mou_details = mou_details.scalars().all()

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    return mou_details
