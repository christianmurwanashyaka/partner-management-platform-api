from datetime import datetime
from typing import Optional
import uuid
from pydantic import BaseModel


class BaseAddressCreate(BaseModel):
    province_state: Optional[str] = None
    district: Optional[str] = None


class BaseAddressRead(BaseModel):
    uuid: uuid.UUID
    province_state: Optional[str] = None
    district: Optional[str] = None
    created_at: datetime
    created_by: str

    class Config:
        from_attributes = True


class OrganizationAddress(BaseAddressRead):
    country: Optional[str] = None
    avenue: Optional[str] = None
    po_box: Optional[str] = None

    class Config:
        from_attributes = True
