from datetime import datetime
from typing import Optional
import uuid
from pydantic import BaseModel


class SubFinancingSchemeList(BaseModel):
    uuid: uuid.UUID
    name: str
    description: Optional[str] = None
    sha_code: str
    created_at: datetime
    created_by: str
    financing_scheme_uuid: Optional[uuid.UUID] = None
    financing_agent_uuid: Optional[uuid.UUID] = None
    health_care_provider_uuid: Optional[uuid.UUID] = None

    class Config:
        from_attributes = True


class SubFinancingSchemeCreate(BaseModel):
    name: str
    description: Optional[str] = None
    sha_code: str
    financing_scheme_uuid: uuid.UUID

    class Config:
        from_attributes = True
