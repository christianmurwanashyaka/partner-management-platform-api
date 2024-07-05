import re
import uuid
from datetime import datetime
from typing import List, Dict

from dateutil.relativedelta import relativedelta
from fastapi import HTTPException, status
from uuid import UUID


def parse_uuids(uuids_str: str) -> List[UUID]:
    try:
        return [UUID(uuid_str) for uuid_str in uuids_str.split(',')]
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail='Invalid UUIDs')


def calculate_time_difference_ms(start_time: datetime, end_time: datetime) -> int:
    time_delta = end_time - start_time
    return int(time_delta.total_seconds() * 1000)


def format_time_difference(milliseconds: int) -> Dict[str, int]:
    seconds = milliseconds // 1000
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    weeks, days = divmod(days, 7)
    months, weeks = divmod(weeks, 4)  # Approximate

    time_dict = {}
    if months > 0:
        time_dict['months'] = months
    if weeks > 0:
        time_dict['weeks'] = weeks
    if days > 0:
        time_dict['days'] = days
    if hours > 0:
        time_dict['hours'] = hours
    if minutes > 0:
        time_dict['minutes'] = minutes
    if seconds > 0 or not time_dict:
        time_dict['seconds'] = seconds

    return time_dict