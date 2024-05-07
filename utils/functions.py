from typing import List

from fastapi import HTTPException, status
from uuid import UUID


def parse_uuids(uuids_str: str) -> List[UUID]:
    try:
        return [UUID(uuid_str) for uuid_str in uuids_str.split(',')]
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail='Invalid UUIDs')