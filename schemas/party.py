from typing import List, Optional

from pydantic import BaseModel, Field
from uuid import UUID


class PartyBase(BaseModel):
    name: str = Field(..., description="Name of the party")
    responsibilities: List[str] = Field(..., description="List of responsibilities for the party")
    signatory: str = Field(..., description="Signatory of the party")

    class Config:
        from_attributes: True


class PartyCreate(PartyBase):
    organization_id: Optional[UUID] = Field(default=None, description="ID of the organization this party belongs to")


class PartyUpdate(PartyBase):
    name: Optional[str] = Field(None, description="Name of the party")


class PartyRead(PartyBase):
    uuid: UUID
    organization_id: Optional[UUID] = Field(default=None, description="ID of the organization this party belongs to")
