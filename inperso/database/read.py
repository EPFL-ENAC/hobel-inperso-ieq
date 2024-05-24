import logging
import time

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
