from influxdb_client import InfluxDBClient

from inperso.config import db


client = InfluxDBClient(
    url=db["url"],
    token=db["token"],
    org=db["org"]
)


write_api = client.write_api()
print(write_api)
