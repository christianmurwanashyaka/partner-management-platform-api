from datetime import datetime, date
from typing import List, Optional

import uuid
from pydantic import BaseModel

from schemas.domain_intervention import DomainInterventionList
from schemas.input_detail import InputDetailCreate, InputDetailRead
from schemas.sub_domain import SubDomainList
from schemas.sub_domain_function import SubDomainFunctionRead
from schemas.sub_function import SubFunctionRead


class ActivityDomain(BaseModel):
    domain_intervention_id: uuid.UUID
    sub_domain_id: uuid.UUID
    sub_domain_function_id: uuid.UUID
    sub_function_id: uuid.UUID

    class Config:
        from_attributes = True


class ActivityDomainUpdate(ActivityDomain):
    class Config:
        from_attributes = True


class ActivityDomainDetail(BaseModel):
    domain_intervention: DomainInterventionList
    sub_domain: SubDomainList
    sub_domain_function: SubDomainFunctionRead
    sub_function: SubFunctionRead

    class Config:
        from_attributes = True


class OperationalZoneCreate(BaseModel):
    province: str
    district: str

    class Config:
        from_attributes = True


class OperationalZoneRead(BaseModel):
    uuid: uuid.UUID
    province: str
    district: str
    created_at: datetime
    created_by: str

    class Config:
        from_attributes = True


class ActivityCreate(BaseModel):
    project_id: uuid.UUID
    description: Optional[str] = None
    name: str
    start_date: date
    end_date: date
    implementer: str
    implementer_unit: str
    fiscal_year: str
    domains: List[ActivityDomain]
    input_details: List[InputDetailCreate]

    class Config:
        from_attributes = True


class ActivityList(BaseModel):
    uuid: uuid.UUID
    project_id: uuid.UUID
    name: str
    implementer: str
    implementer_unit: str
    fiscal_year: str
    input_details: List[InputDetailRead]
    start_date: date
    end_date: date
    domains: List[ActivityDomainDetail]

    class Config:
        from_attributes = True


class ActivityRead(BaseModel):
    uuid: uuid.UUID
    project_id: uuid.UUID
    name: str
    description: Optional[str] = None
    implementer: str
    implementer_unit: str
    fiscal_year: str
    start_date: date
    end_date: date
    domains: List[ActivityDomainDetail]
    input_details: List[InputDetailRead]
    created_at: datetime
    created_by: str

    class Config:
        from_attributes = True


class ActivityUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    implementer: Optional[str] = None
    implementer_unit: Optional[str] = None
    fiscal_year: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None

    class Config:
        from_attributes = True


class OperationalZoneUpdate(OperationalZoneCreate):

    class Config:
        from_attributes = True
