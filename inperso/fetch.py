"""Function to manually fetch data from the database"""

import logging
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
) -> list[dict]:
    """Fetch data from the database.

    Args:
        datetime_start (datetime, optional): Start of the time range.
            Defaults to None, which retrieve data from timestamp 0.
        datetime_end (datetime, optional): End of the time range.
            Defaults to None, which retrieve data until now.
        frequency (str, optional): If provided with "window_size", resample the
            data using a moving average. Example: "6h".
        window_size (str, optional): If provided with "frequency", resample the
            data using a moving average. Example: "1d".
        brands (list[str], optional): List of brands to retrieve data from.
            Defaults to None, which retrieves data from all brands.
        devices (list[str], optional): List of devices to retrieve data from.
            Defaults to None, which retrieves data from all devices.
        fields (list[str], optional): List of fields to retrieve data from.
            Defaults to None, which retrieves data from all fields.

    Returns:
        list[dict]: List of dictionaries containing the data, with the keys:
            - "time" (datetime)
            - "value" (any)
            - "field" (str)
            - "device" (str)
    """
    query_str = f'from(bucket:"{config.db["bucket"]}")'
    query_str += _get_datetime_filter(datetime_start, datetime_end)
    query_str += _get_brands_filter(brands)
    query_str += _get_devices_filter(devices)
    query_str += _get_fields_filter(fields)
    query_str += _get_moving_average_filter(frequency, window_size)
    query_str += '|> keep(columns: ["_time", "_value", "_field", "device"])'

    logging.info("Running the query:\n" + query_str.replace("|>", "\n|>"))
    result = query(query_str)
    values = [record.values for table in result for record in table.records]

    # Remove "result" and "table" keys
    values = [
        {
            "time": record["_time"],
            "value": record["_value"],
            "field": record["_field"],
            "device": record["device"],
        }
        for record in values
    ]

    return values


def _get_datetime_filter(
    datetime_start: Optional[datetime] = None,
    datetime_end: Optional[datetime] = None,
) -> str:
    if datetime_start is None:
        datetime_start = datetime.fromtimestamp(0)
    timestamp_start = int(datetime_start.timestamp())

    if datetime_end is None:
        datetime_end = datetime.now()
    timestamp_end = int(datetime_end.timestamp())

    return f"|> range(start: {timestamp_start}, stop: {timestamp_end})"


def _get_moving_average_filter(
    frequency: Optional[str] = None,
    window_size: Optional[str] = None,
) -> str:
    if frequency is None and window_size is None:
        return ""

    if frequency is None or window_size is None:
        raise ValueError("Both 'frequency' and 'window_size' must be provided.")

    return f"|> timedMovingAverage(every: {frequency}, period: {window_size})"


def _get_brands_filter(brands: Optional[list[str]] = None) -> str:
    if brands is None:
        return ""

    return f'|> filter(fn: (r) => r["_measurement"] =~ /({"|".join(brands)})/)'


def _get_devices_filter(devices: Optional[list[str]] = None) -> str:
    if devices is None:
        return ""

    return f'|> filter(fn: (r) => r["device"] =~ /({"|".join(devices)})/)'


def _get_fields_filter(fields: Optional[list[str]] = None) -> str:
    if fields is None:
        return ""

    return f'|> filter(fn: (r) => r["_field"] =~ /({"|".join(fields)})/)'
