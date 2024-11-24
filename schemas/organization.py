from typing import Optional, List
import uuid
from pydantic import BaseModel, EmailStr
from schemas.document import DocumentRead
from schemas.financing_scheme import FinancingSchemeList
from schemas.organization_type import OrganizationTypeRead
from schemas.sub_financing_scheme import SubFinancingSchemeList


class OrganizationRead(BaseModel):
    uuid: uuid.UUID
    name: str
    phone_number: str
    email: EmailStr
    website: str
    created_by: str
    home_country_representative: Optional[str] = None
    rwanda_representative: str

    # Direct string address components for output
    home_country: Optional[str] = None
    home_country_province_state: Optional[str] = None
    home_country_district: Optional[str] = None
    home_country_avenue: Optional[str] = None
    home_country_po_box: Optional[str] = None

    rwanda_province: str
    rwanda_district: str
    rwanda_avenue: Optional[str] = None
    rwanda_po_box: Optional[str] = None

    rgb_number: Optional[str] = None

    organization_type: Optional[OrganizationTypeRead] = None
    documents: List[DocumentRead] = []

    financing_schemes: List[FinancingSchemeList] = []
    financing_agents: List[FinancingSchemeList] = []
    health_care_providers: List[FinancingSchemeList] = []
    sub_financing_schemes: List[SubFinancingSchemeList] = []
    sub_financing_agents: List[SubFinancingSchemeList] = []
    sub_health_care_providers: List[SubFinancingSchemeList] = []

    class Config:
        from_attributes = True


class OrganizationUpdate(BaseModel):
    name: Optional[str] = None
    phone_number: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    home_country_representative: Optional[str] = None
    rwanda_representative: Optional[str] = None
    home_country: Optional[str] = None
    home_country_province_state: Optional[str] = None
    home_country_district: Optional[str] = None
    home_country_avenue: Optional[str] = None
    home_country_po_box: Optional[str] = None
    rwanda_province: Optional[str] = None
    rwanda_district: Optional[str] = None
    rwanda_avenue: Optional[str] = None
    rwanda_po_box: Optional[str] = None
    rgb_number: Optional[str] = None
    organization_type_id: Optional[uuid.UUID] = None

    class Config:
        from_attributes = True
