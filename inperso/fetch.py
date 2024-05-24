"""Function to manually fetch data from the database"""

from datetime import datetime
from typing import Optional

from inperso import config
from inperso.database.read import query


def fetch(
    datetime_start: Optional[datetime] = None,
    datetime_end: Optional[datetime] = None,
    frequency: Optional[str] = None,
    window_size: Optional[str] = None,
    brands: Optional[list[str]] = None,
    devices: Optional[list[str]] = None,
    fields: Optional[list[str]] = None,
    **kwargs,
):
    if datetime_start is None:
        datetime_start = datetime.fromtimestamp(0)
    timestamp_start = int(datetime_start.timestamp())

    if datetime_end is None:
        datetime_end = datetime.now()
    timestamp_end = int(datetime_end.timestamp())

    query_str = (
        f'from(bucket:"{config.db["bucket"]}") '
        f"|> range(start: {timestamp_start}, stop: {timestamp_end}) "
        '|> keep(columns: ["_time", "_value", "_field", "device"])'
    )

    result = query(query_str)
    return result
