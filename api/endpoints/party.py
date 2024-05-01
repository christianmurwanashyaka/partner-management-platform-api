from fastapi import APIRouter, HTTPException, Depends, Body, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from db.database import get_db
from db.models import Party
from schemas.party import PartyRead, PartyCreate

router = APIRouter()


@router.post('/', response_model=PartyRead)
async def create_party(request: Request, party_data: PartyCreate, db: AsyncSession = Depends(get_db)):
    new_party = Party(**party_data.dict())
    print('NEW PART ::::::::::::', new_party)
    db.add(new_party)
    await db.commit()
    await db.refresh(new_party)
    return new_party
