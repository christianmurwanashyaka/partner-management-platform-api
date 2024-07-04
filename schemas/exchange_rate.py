from datetime import datetime
from pydantic import BaseModel
import uuid

from db.models import Currency


class ExchangeRateCreate(BaseModel):
    currency: Currency
    rate: float


class ExchangeRateRead(BaseModel):
    uuid: uuid.UUID
    currency: Currency
    rate: float
    created_at: datetime
    created_by: str

    class Config:
        from_attributes = True
