from enum import Enum

from sqlmodel import Field

from db.models import CommonBaseModel


class Currency(str, Enum):
    RWF = "RWF"
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"


class CurrencyExchangeRate(CommonBaseModel, table=True):
    __tablename__ = "currency_exchange_rate"

    currency: Currency = Field(default=Currency.RWF, index=True)
    rate: float = Field(default=1.0, description="Exchange rate relative to RWF")
