from influxdb_client import InfluxDBClient

from inperso import config

client = InfluxDBClient(
    url=config.db["url"],
    token=config.db["token"],
    org=config.db["org"],
    enable_gzip=True,
)

query_api = client.query_api()


def query(query: str):
    """Query the database (with a Flux query) and return the result."""

    return query_api.query(query)
