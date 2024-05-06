from influxdb_client import InfluxDBClient

from inperso import config
from inperso.utils import poll


def get_query_api():
    client = InfluxDBClient(
        url=config.db["url"],
        token=config.db["token"],
        org=config.db["org"],
        enable_gzip=True,
    )

    query_api = client.query_api()
    return query_api


@poll(
    maximum_retries=config.db["maximum_query_retries"],
    delay=config.db["query_retry_delay_seconds"],
    fail_message="Failed to query the database",
)
def query(query: str) -> list:
    """Query the database (with a Flux query) and return the result."""

    query_api = get_query_api()
    response = query_api.query(query)
    return response
