from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from api.dependencies.access_control import admin_access
from api.dependencies.auth import get_current_user
from db.database import get_db
from db.models import CurrencyExchangeRate, User
from helpers.db import check_if_exists
from schemas.exchange_rate import ExchangeRateRead, ExchangeRateCreate

router = APIRouter()


@router.post("/", response_model=ExchangeRateRead, dependencies=[Depends(admin_access)])
async def create_currency_exchange_rate(
        request: Request,
        exchange_rate_data: ExchangeRateCreate,
        db: AsyncSession = Depends(get_db)):
    user = request.state.user.email

    if await check_if_exists(CurrencyExchangeRate, db, currency=exchange_rate_data.currency):
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Currency exchange rate already exists")

    new_exchange_rate = CurrencyExchangeRate(currency=exchange_rate_data.currency, rate=exchange_rate_data.rate, created_by=user)

    db.add(new_exchange_rate)
    await db.commit()
    await db.refresh(new_exchange_rate)
    return new_exchange_rate


@router.get('/', response_model=List[ExchangeRateRead])
async def get_exchange_rates(db: AsyncSession = Depends(get_db)):
    query = select(CurrencyExchangeRate).where(CurrencyExchangeRate.deleted_status == False).order_by(CurrencyExchangeRate.created_at.desc())

    result = await db.execute(query)
    exchange_rates = result.scalars().unique().all()

    return exchange_rates
