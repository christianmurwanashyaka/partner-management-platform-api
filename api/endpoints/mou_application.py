from typing import List

from fastapi import APIRouter, Request, Depends, status, HTTPException
from sqlalchemy import select
from sqlmodel.ext.asyncio.session import AsyncSession

from api.dependencies.access_control import partner_access
from api.dependencies.auth import get_current_user
from db.database import get_db
from db.models import User, MouDetail, MouApplication, Document, DocumentType
from helpers.db import get_first_item
from schemas.mou_application import MouApplicationRead, MouApplicationCreate
from utils.files import generate_mou_action_plan

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

        file_path, filename = await generate_mou_action_plan(new_mou_application)

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


@router.get('/', response_model=List[MouApplicationRead])
async def get_mou_applications(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role in ['admin', 'swapteam_member']:
        query = select(MouApplication)
    elif current_user.role == 'partner':
        query = select(MouApplication).filter(MouApplication.created_by == current_user.email)
    else:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail='You are not authorized to perform this action')

    mou_applications = await db.execute(query)
    mou_applications = mou_applications.scalars().all()

    return mou_applications


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