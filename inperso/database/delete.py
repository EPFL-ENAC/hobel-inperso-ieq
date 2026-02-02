import logging
from datetime import datetime, timezone

from influxdb_client import InfluxDBClient

from inperso import config
from inperso.utils import utc_datetime_to_iso


def get_delete_api():
    client = InfluxDBClient(
        url=config.db["host"],
        token=config.db["token"],
        org=config.db["org"],
        enable_gzip=True,
    )

    delete_api = client.delete_api()

    return delete_api


def delete(bucket: str, predicate: str) -> None:
    """Delete data from a bucket based on a predicate."""

    datetime_start = datetime(1970, 1, 1, tzinfo=timezone.utc)
    datetime_end = datetime.now(timezone.utc)
    delete_api = get_delete_api()

    logging.info(f"Deleting data from bucket '{bucket}' with predicate '{predicate}'.")

    delete_api.delete(
        org=config.db["org"],
        bucket=bucket,
        start=utc_datetime_to_iso(datetime_start),
        stop=utc_datetime_to_iso(datetime_end),
        predicate=predicate,
    )
