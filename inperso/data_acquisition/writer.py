from influxdb_client import InfluxDBClient

from inperso import config

client = InfluxDBClient(url=config.db["url"], token=config.db["token"], org=config.db["org"])


write_api = client.write_api()
print(write_api)
