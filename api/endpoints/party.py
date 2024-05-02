from typing import List

from fastapi import APIRouter, HTTPException, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from api.dependencies.access_control import partner_access
from api.dependencies.auth import get_current_user
from db.database import get_db
from db.models import Party, User
from schemas.party import PartyRead, PartyCreate

router = APIRouter()


@router.post('/', response_model=PartyRead, dependencies=[Depends(partner_access)])
async def create_party(request: Request, party_data: PartyCreate, db: AsyncSession = Depends(get_db)):
    user = request.state.user.email
    new_party = Party(
        name=party_data.name,
        type=party_data.type,
        responsibilities=party_data.responsibilities,
        signatory=party_data.signatory,
        organization_id=party_data.organization_id,
        created_by=user
    )
    try:
        db.add(new_party)
        await db.commit()
        await db.refresh(new_party)
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    return new_party


@router.get('/', response_model=List[PartyRead], dependencies=[Depends(partner_access)])
async def get_user_parties(request: Request, db: AsyncSession = Depends(get_db)):
    user = request.state.user.email

    try:
        parties = await db.execute(select(Party).where(Party.created_by == user))
        parties = parties.scalars().all()

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    return parties
