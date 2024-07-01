from typing import Optional, List, Union
from urllib.parse import unquote

from uuid import UUID


def parse_uuid_list(value: Optional[Union[str, List[str]]]) -> Optional[List[UUID]]:
    if value is None:
        return None

    if isinstance(value, list):
        # If it's already a list, process each item
        decoded_values = [unquote(item) for item in value]
    else:
        # If it's a string, first URL-decode, then split by comma
        decoded_values = unquote(value).split(',')

    # Parse each value into a UUID, skipping any that are invalid
    uuids = []
    for item in decoded_values:
        try:
            uuids.append(UUID(item.strip()))
        except ValueError:
            # Skip invalid UUIDs
            continue

    return uuids if uuids else None


def parse_string_list(value: Optional[Union[str, List[str]]]) -> Optional[List[str]]:
    if value is None:
        return None
    if isinstance(value, list):
        # If it's already a list, return it after stripping whitespace and decoding
        return [unquote(item.strip()) for item in value if item.strip()]
    # If it's a string, URL-decode and split by comma
    return [item.strip() for item in unquote(value).split(',') if item.strip()]