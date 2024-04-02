import logging
from datetime import datetime

import requests

from inperso import config
from inperso.data_acquisition.retriever import Retriever


class UhooRetriever(Retriever):
    def _check_datetimes(
        self,
        datetime_start: datetime,
        datetime_end: datetime,
    ) -> None:
        """Check that the datetimes are valid and span at most 1 hour."""

        super()._check_datetimes(datetime_start, datetime_end)

        if (datetime_end - datetime_start).seconds > 3600:
            raise ValueError("The interval spans more than 1 hour.")

    def _fetch(
        self,
        datetime_start: datetime,
        datetime_end: datetime,
    ) -> dict:
        """Retrieve data from the source and return it."""

        token = get_token(config.uhoo["client_id"])
        devices = get_device_list(token)

        data = {}

        for device in devices:
            device_name = device["deviceName"]
            device_mac = device["macAddress"]

            try:
                device_data = get_device_data(token, device_mac, datetime_start, datetime_end)

            except RuntimeError:
                continue

            if device_data == {}:
                continue

            data[device_name] = device_data["data"]

        return data

    def _get_line_queries(self) -> list[str]:
        """Get line queries from stored data dictionary."""

        queries = []

        for device_name, device_data in self.data.items():
            for entry in device_data:
                fields = entry.copy()
                timestamp = fields.pop("timestamp")

                queries.append(
                    format_line_query(
                        measurement="uhoo",
                        tags={"device": device_name},
                        fields=fields,
                        timestamp=timestamp,
                    )
                )

        return queries


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
    header = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(url, headers=header)

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
) -> dict:
    """Get the data of one device.

    datetime_start and datetime_end must span at most 1 hour.
    """

    logging.info(f"Getting Uhoo device data for {device_mac}")

    timestamp_start = int(datetime_start.timestamp())
    timestamp_end = int(datetime_end.timestamp())

    url = "https://api.uhooinc.com/v1/devicedata"
    header = {"Authorization": f"Bearer {access_token}"}
    data = {
        "macAddress": device_mac,
        "mode": "minute",
        "timestampStart": timestamp_start,
        "timestampEnd": timestamp_end,
    }
    response = requests.post(url, headers=header, data=data)

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


def format_line_query(
    measurement: str,
    tags: dict,
    fields: dict,
    timestamp: int,
) -> str:
    """Format a line query for InfluxDB."""

    tags_str = ",".join([f"{key}={value}".replace(" ", "_") for key, value in tags.items()])
    fields_str = ",".join([f"{key}={value}".replace(" ", "_") for key, value in fields.items()])

    return f"{measurement},{tags_str} {fields_str} {timestamp}"
