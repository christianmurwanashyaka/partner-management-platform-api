from datetime import datetime
from typing import Optional

import uuid
from pydantic import BaseModel

from db.models.document import DocumentType


class DocumentRead(BaseModel):
    uuid: uuid.UUID
    name: str
    description: Optional[str] = None
    document_type: DocumentType
    path: str
    filename: str
    registration: bool
    created_at: datetime
    created_bg: str

    class Config:
        from_attributes = True
