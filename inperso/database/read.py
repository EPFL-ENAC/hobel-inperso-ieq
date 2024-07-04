import logging
import time
from datetime import datetime
from typing import Optional

from influxdb_client import InfluxDBClient

from inperso import config


def get_query_api():
    client = InfluxDBClient(
        url=config.db["host"],
        token=config.db["token"],
        org=config.db["org"],
        enable_gzip=True,
    )

    query_api = client.query_api()
    return query_api


def query(query: str):
    """Query the database (with a Flux query) and return the result."""

    response = None

    for attempt in range(config.db["maximum_query_retries"]):
        try:
            query_api = get_query_api()
            response = query_api.query(query)
            break

        except Exception as e:
            logging.error(
                f"Failed to query the database (attempt {attempt + 1}/{config.db['maximum_query_retries']}): {e}"
            )
            time.sleep(config.db["query_retry_delay_seconds"])

    return response


def get_datetime_filter(
    datetime_start: Optional[datetime] = None,
    datetime_end: Optional[datetime] = None,
) -> str:
    """Get a query substring to filter data by datetime range."""

    if datetime_start is None:
        datetime_start = datetime.fromtimestamp(0)
    timestamp_start = int(datetime_start.timestamp())

    if datetime_end is None:
        datetime_end = datetime.now()
    timestamp_end = int(datetime_end.timestamp())

    return f"|> range(start: {timestamp_start}, stop: {timestamp_end})"
