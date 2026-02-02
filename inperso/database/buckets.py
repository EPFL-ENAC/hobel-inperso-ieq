import logging

from influxdb_client import InfluxDBClient

from inperso import config


def get_buckets_api():
    client = InfluxDBClient(
        url=config.db["host"],
        token=config.db["token"],
        org=config.db["org"],
        enable_gzip=True,
    )

    buckets_api = client.buckets_api()

    return buckets_api


def ensure_bucket_exists(bucket_name: str) -> None:
    """Check whether a bucket exists in the database, and create it if not."""

    buckets_api = get_buckets_api()
    bucket = buckets_api.find_bucket_by_name(bucket_name)

    if bucket is not None:
        return

    logging.info(f"Bucket '{bucket_name}' does not exist. Creating it.")
    buckets_api.create_bucket(bucket_name=bucket_name, org=config.db["org"])
    logging.info(f"Bucket '{bucket_name}' created successfully.")
