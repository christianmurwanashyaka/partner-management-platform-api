from typing import Optional, List, Union
from urllib.parse import unquote

from uuid import UUID


def parse_uuid_list(value: Optional[Union[str, List[str]]]) -> Optional[List[UUID]]:
    if value is None:
        return None

    # If it's already a list, process each item
    if isinstance(value, list):
        # Check if the list contains a single string that needs to be split
        if len(value) == 1 and isinstance(value[0], str):
            # Split the single string by commas
            decoded_values = unquote(value[0]).split(',')
        else:
            # If the list is not just a single comma-separated string, process normally
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
    print('VALUE: ', value)
    # If it's already a list, process each item
    if isinstance(value, list):
        # Check if the list contains a single string that needs to be split
        if len(value) == 1 and isinstance(value[0], str):
            # Split the single string by commas
            return [item.strip() for item in unquote(value[0]).split(',') if item.strip()]
        # Otherwise, process the list normally
        return [unquote(item.strip()) for item in value if item.strip()]

    # If it's a string, URL-decode and split by comma
    return [item.strip() for item in unquote(value).split(',') if item.strip()]