from typing import Optional

import uuid
from fastapi import APIRouter, Request, Depends, HTTPException, status, Form, File, UploadFile
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError
from sqlmodel.ext.asyncio.session import AsyncSession

from api.dependencies.access_control import partner_access, admin_access, swapteam_member_access
from api.dependencies.auth import get_current_user
from db.database import get_db
from db.models.organization import Organization
from db.models.document import Document, DocumentType
from db.models.pagination import PaginatedResponse
from db.models.user import User
from schemas.organization import OrganizationRead
from helpers.db import check_if_exists, get_all_items, get_first_item
from utils.files import handle_upload_file

router = APIRouter()


@router.post("/", response_model=OrganizationRead, dependencies=[Depends(partner_access)])
async def create_organization(
        request: Request,
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
        rwanda_avenue: str = Form(...),
        rwanda_po_box: str = Form(...),
        organization_type_id: uuid.UUID = Form(...),
        appointment_letter: UploadFile = File(...),
        notified_constitution_bylaws: Optional[UploadFile] = File(None),
        db: AsyncSession = Depends(get_db),
):
    if await check_if_exists(Organization, db, name=name):
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Organization with this name already exists")
    user = request.state.user.email

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
        organization_type_id=organization_type_id,
        created_by=user,
    )
    try:
        db.add(new_organization)
        await db.commit()
        await db.refresh(new_organization)

        # Handle file uploads
        appointment_letter_path, appointment_letter_filename = await handle_upload_file(appointment_letter)
        appointment_letter_doc = Document(
            name="Appointment Letter",
            document_type=DocumentType.APPOINTMENT_LETTER,
            path=appointment_letter_path,
            filename=appointment_letter_filename,
            organization=new_organization,
            created_by=user
        )
        db.add(appointment_letter_doc)

        if notified_constitution_bylaws:
            notified_path, notified_filename = await handle_upload_file(notified_constitution_bylaws)
            notified_constitution_bylaws_doc = Document(
                name="Notified Constitution Bylaws",
                document_type=DocumentType.NOTIFIED_CONSTITUTION_BYLAWS,
                path=notified_path,
                filename=notified_filename,
                organization=new_organization,
                created_by=user
            )
            db.add(notified_constitution_bylaws_doc)

        await db.commit()
    except IntegrityError as e:
        await db.rollback()
        if "duplicate key value violates unique constraint" in str(e):

            # Extract the duplicate key value from the error message
            duplicate_key = str(e).split("=")[1].split(")")[0]
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Organization with {duplicate_key}) already exists"
            )
        else:

            # Handle other types of IntegrityError
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid data provided"
            )
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    return new_organization


@router.get('/', response_model=PaginatedResponse[OrganizationRead], dependencies=[Depends(swapteam_member_access)])
async def get_organizations(page: int = 1, page_size: int = 100, db: AsyncSession = Depends(get_db)):
    return await get_all_items(db, Organization, page=page, page_size=page_size)


@router.get('/{uuid}', response_model=OrganizationRead)
async def get_organization(uuid: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    query = select(Organization).filter(Organization.uuid == uuid)
    organization = await get_first_item(db, query)

    if not organization:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail='Organization not found')

    if current_user.role in ['admin', 'swapteam_member']:
        return organization
    elif current_user.role == 'partner' and organization.created_by == current_user.email:
        return organization
    else:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail='You are not authorized to perform this action')
