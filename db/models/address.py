from typing import Optional

from db.models.base import CommonBaseModel


class BaseAddress(CommonBaseModel):
    province_state: Optional[str] = None
    district: Optional[str] = None
