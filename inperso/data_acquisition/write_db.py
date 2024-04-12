from influxdb_client import InfluxDBClient, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

from inperso import config

client = InfluxDBClient(
    url=config.db["url"],
    token=config.db["token"],
    org=config.db["org"],
    enable_gzip=True,
)

write_api = client.write_api(write_options=SYNCHRONOUS)


def write(queries: list[dict]):
    """Write queries (dictionaries) into the database.

    Timestamps must be in UTC with second precision.
    """

    write_api.write(bucket=config.db["bucket"], record=queries, write_precision=WritePrecision.S)