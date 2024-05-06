import csv
import logging
from datetime import datetime, timedelta

import requests

from inperso import config
from inperso.data_acquisition.retriever import Retriever
from inperso.utils import dict_ints_to_floats


class UhooRetriever(Retriever):
    def __init__(self) -> None:
        super().__init__()

        token = get_token(config.uhoo["client_id"])
        self.devices = get_device_list(token)
        logging.info(f"Found {len(self.devices)} devices")

    @property
    def _measurement_name(self) -> str:
        return "uhoo"

    @property
    def _fetch_interval(self) -> timedelta:
        return timedelta(hours=config.uhoo["fetch_interval_hours"])

    def _fetch(
        self,
        datetime_start: datetime,
        datetime_end: datetime,
    ) -> None:
        """Retrieve data from the source."""

        token = get_token(config.uhoo["client_id"])

        for device in self.devices:
            device_name = device["deviceName"]
            device_mac = device["macAddress"]

            try:
                logging.info(f"Getting Uhoo device data for {device_name} ({device_mac})")
                device_data = get_device_data(token, device_mac, datetime_start, datetime_end)

            except RuntimeError:
                continue

            if device_data == {}:
                continue

            device_location = device["roomName"]
            device_floor = device["floorNumber"]

            for entry in device_data["data"]:
                fields = entry.copy()
                timestamp = fields.pop("timestamp")
                fields = dict_ints_to_floats(fields)

                self.add_write_query({
                    "measurement": self._measurement_name,
                    "tags": {
                        "device": device_name,
                        "location": device_location,
                        "floor": device_floor,
                    },
                    "fields": fields,
                    "time": timestamp,
                })

    def _fetch_from_file(
        self,
        file_path: str,
        device_name: str,
    ) -> None:
        """Retrieve data from a file."""

        devices_by_name = {device["deviceName"]: device for device in self.devices}
        if device_name not in devices_by_name:
            logging.warning(f"Device {device_name} not found, skipping")
            return

        device = devices_by_name[device_name]
        device_location = device["roomName"]
        device_floor = device["floorNumber"]

        tags = {
            "device": device_name,
            "location": device_location,
            "floor": device_floor,
        }

        with open(file_path, "r") as file:
            reader = csv.DictReader(
                file,
                fieldnames=[
                    "Date and Time",
                    "Temperature",
                    "Relative Humidity",
                    "PM2.5",
                    "TVOC",
                    "CO2",
                    "CO",
                    "Air Pressure",
                    "Ozone",
                    "NO2",
                    "PM1",
                    "PM4",
                    "PM10",
                    "Formaldehyde",
                    "Light",
                    "Sound",
                    "Virus Index",
                    "Hydrogen Sulfide",
                    "Ammonia",
                    "Nitric Oxide",
                    "Sulphur Dioxide",
                    "Oxygen",
                ],
            )
            next(reader)  # Skip header

            for row in reader:
                timestamp = int(datetime.fromisoformat(row["Date and Time"]).timestamp())

                fields = {
                    "virusIndex": row["Virus Index"],
                    "temperature": row["Temperature"],
                    "humidity": row["Relative Humidity"],
                    "pm25": row["PM2.5"],
                    "tvoc": row["TVOC"],
                    "co2": row["CO2"],
                    "co": row["CO"],
                    "airPressure": row["Air Pressure"],
                    "ozone": row["Ozone"],
                    "no2": row["NO2"],
                    "pm1": row["PM1"],
                    "pm4": row["PM4"],
                    "pm10": row["PM10"],
                    "ch2o": row["Formaldehyde"],
                    "light": row["Light"],
                    "sound": row["Sound"],
                    "h2s": row["Hydrogen Sulfide"],
                    "no": row["Nitric Oxide"],
                    "so2": row["Sulphur Dioxide"],
                    "nh3": row["Ammonia"],
                    "oxygen": row["Oxygen"],
                }
                fields = {k: float(v) for k, v in fields.items() if v != ""}

                self.add_write_query({
                    "measurement": self._measurement_name,
                    "tags": tags,
                    "fields": fields,
                    "time": timestamp,
                })


def get_token(client_id: str) -> str:
    """Get an access token from a private client ID, valid 10 minutes."""

    logging.info("Getting Uhoo client token")

    url = "https://api.uhooinc.com/v1/generatetoken"
    data = {"code": client_id}
    response = requests.post(url, data=data)

    if response.status_code != 200:
        message = f"Failed to get token: Response {response.status_code} - {response.text}"
        logging.error(message)
        raise RuntimeError(message)

    data = response.json()

    access_token = data["access_token"]
    # refresh_token = data["refresh_token"]

    return access_token


def get_device_list(access_token: str) -> list:
    """Get the list of devices, including their MAC addresses."""

    logging.info("Getting Uhoo device list")

    url = "https://api.uhooinc.com/v1/devicelist"
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        message = f"Failed to get device list: Response {response.status_code} - {response.text}"
        logging.error(message)
        raise RuntimeError(message)
        # 400: limit exceeded
        # 401: invalid token

    return response.json()


def get_device_data(
    access_token: str,
    device_mac: str,
    datetime_start: datetime,
    datetime_end: datetime,
) -> dict[str, list[dict]]:
    """Get the data of one device.

    datetime_start and datetime_end must span at most 1 hour.
    Returns {} or a dictionary with the following structure: {
        "data": [
            {
                "timestamp": datetime,
                "field1": value1,
                "field2": value2,
                ...
            },
            ...
        ],
    }
    """

    timestamp_start = int(datetime_start.timestamp())
    timestamp_end = int(datetime_end.timestamp())

    url = "https://api.uhooinc.com/v1/devicedata"
    headers = {"Authorization": f"Bearer {access_token}"}
    data = {
        "macAddress": device_mac,
        "mode": "minute",
        "timestampStart": timestamp_start,
        "timestampEnd": timestamp_end,
    }
    response = requests.post(url, headers=headers, data=data)

    if response.status_code == 404:  # No data available
        logging.warning(f"No data available for {device_mac}")
        return {}

    if response.status_code != 200:
        message = f"Failed to get device data: Response {response.status_code} - {response.text}"
        logging.error(message)
        raise RuntimeError(message)
        # 400: limit exceeded
        # 401: invalid token
        # 403: expired token

    return response.json()
