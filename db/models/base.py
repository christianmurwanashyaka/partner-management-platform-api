from datetime import datetime
from typing import Union

import uuid as pk
from sqlalchemy import func
from sqlmodel import SQLModel, Field


class BaseFields(SQLModel):
    uuid: pk.UUID = Field(default_factory=pk.uuid4, nullable=False, index=True, unique=True)
    created_at: datetime = Field(default_factory=datetime.now, sa_column_kwargs={"nullable": False, "index": True})
    created_by: Union[str, None] = Field(nullable=False)


class CommonBaseModel(BaseFields):
    id: Union[int, None] = Field(default=None, primary_key=True, nullable=False)
    deleted_status: bool = Field(default=False)
    last_updated_at: Union[datetime, None] = Field(sa_column_kwargs={"onupdate": func.now()})
    last_updated_by: Union[str, None] = Field(nullable=True)
    deleted_by: Union[str, None] = Field(nullable=True)
