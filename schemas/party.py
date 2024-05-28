from typing import List, Optional
from pydantic import BaseModel, Field
from uuid import UUID


class PartyBase(BaseModel):
    name: str = Field(..., description="Name of the party")
    responsibilities: List[str] = Field(..., description="List of responsibilities for the party")
    signatory: str = Field(..., description="Signatory of the party")
    position: Optional[str] = None

    class Config:
        from_attributes: True


class PartyCreate(PartyBase):
    organization_id: Optional[UUID] = Field(default=None, description="ID of the organization this party belongs to")


class PartyUpdate(BaseModel):
    name: Optional[str] = None
    responsibilities: Optional[List[str]] = None
    signatory: Optional[str] = None
    position: Optional[str] = None

    class Config:
        from_attributes: True


class PartyRead(PartyBase):
    uuid: UUID
    organization_id: Optional[UUID] = Field(default=None, description="ID of the organization this party belongs to")

    class Config:
        from_attributes = True
