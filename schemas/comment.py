from datetime import datetime

import uuid
from typing import Optional

from pydantic import BaseModel

from schemas.mou_application import MouApplicationRead
from schemas.user import UserProfile


class MouCommentRead(BaseModel):
    uuid: uuid.UUID
    content: str
    user: UserProfile
    created_at: datetime
    created_by: str

    class Config:
        from_attributes = True
