from typing import List

import uuid
from fastapi import APIRouter, HTTPException, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from api.dependencies.access_control import partner_access
from api.dependencies.auth import get_current_user
from db.database import get_db
from db.models import Party, User, UserRole
from schemas.party import PartyRead, PartyCreate, PartyUpdate

router = APIRouter()


@router.post('/', response_model=PartyRead, dependencies=[Depends(partner_access)])
async def create_party(request: Request, party_data: PartyCreate, db: AsyncSession = Depends(get_db)):
    user = request.state.user.email
    new_party = Party(
        name=party_data.name,
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


@router.patch('/{uuid}', response_model=PartyRead, dependencies=[Depends(partner_access)])
async def update_party(uuid: uuid.UUID, party_update: PartyUpdate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        query = select(Party).where(Party.uuid == uuid)
        result = await db.execute(query)
        party = result.scalar_one_or_none()

        if not party:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Party not found')

        if party.created_by != current_user.email and current_user.role != UserRole.ADMIN:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Not authorized to update this party')

        for key, value in party_update.dict(exclude_unset=True).items():
            setattr(party, key, value)

        await db.commit()
        await db.refresh(party)

        return party
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
