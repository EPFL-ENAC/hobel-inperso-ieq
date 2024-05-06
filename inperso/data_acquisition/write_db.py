from datetime import datetime
from typing import TypedDict

from influxdb_client import InfluxDBClient, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

from inperso import config
from inperso.utils import poll


def get_write_api():
    client = InfluxDBClient(
        url=config.db["url"],
        token=config.db["token"],
        org=config.db["org"],
        enable_gzip=True,
    )

    write_api = client.write_api(write_options=SYNCHRONOUS)

    return write_api


class WriteQuery(TypedDict):
    measurement: str
    tags: dict
    fields: dict
    time: datetime | int  # Unix timestamp


@poll(
    maximum_retries=config.db["maximum_query_retries"],
    delay=config.db["query_retry_delay_seconds"],
    fail_message="Failed to write data to the database",
)
def write(queries: list[WriteQuery]) -> None:
    """Write queries (dictionaries) into the database.

    Timestamps must be in UTC with second precision.
    """

    write_api = get_write_api()
    write_api.write(bucket=config.db["bucket"], record=queries, write_precision=WritePrecision.S)
