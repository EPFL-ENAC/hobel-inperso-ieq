import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from typing import Optional

import requests

from inperso import config
from inperso.data_acquisition.retriever import Retriever
from inperso.utils import dict_ints_to_floats, utc_datetime_to_iso

accounts_api_url = "https://accounts-api.airthings.com/v1/"
api_url = "https://ext-api.airthings.com/v1/"


class AirthingsRetriever(Retriever):
    @property
    def _measurement_name(self) -> str:
        return "airthings"

    @property
    def _fetch_interval(self) -> timedelta:
        return timedelta(hours=config.airthings["fetch_interval_hours"])

    def _fetch(
        self,
        datetime_start: datetime,
        datetime_end: datetime,
    ) -> None:
        """Retrieve data from the source."""

        token = get_token(config.airthings["api_id"], config.airthings["api_key"])
        device_list = get_device_list(token)
        logging.info(f"Found {len(device_list)} Airthings devices.")

        with ThreadPoolExecutor() as executor:
            futures = [
                executor.submit(self._fetch_device_data, token, device, datetime_start, datetime_end)
                for device in device_list
            ]
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    logging.error(f"Error fetching device data: {e}")

    def _fetch_device_data(
        self,
        token: str,
        device: dict,
        datetime_start: datetime,
        datetime_end: datetime,
    ) -> None:
        """Retrieve data for a single device."""
        device_id = device["id"]

        try:
            device_data = get_device_samples(
                access_token=token,
                device_id=device_id,
                datetime_start=datetime_start,
                datetime_end=datetime_end,
            )
        except Exception as e:
            logging.error(f"Failed to get data for device {device_id}: {e}")
            return

        device_name = device["segment"]["name"]
        device_type = device["deviceType"]
        device_location = device["location"]["name"]

        for i in range(len(device_data["time"])):
            fields = {}

            for key in device_data:
                if key == "time":
                    continue

                data = device_data[key][i]

                if data is None:
                    continue

                fields[key] = data

            timestamp = device_data["time"][i]
            fields = dict_ints_to_floats(fields)

            self.add_write_query({
                "measurement": self._measurement_name,
                "tags": {
                    "device": device_name,
                    "type": device_type,
                    "location": device_location,
                },
                "fields": fields,
                "time": timestamp,
            })


def get_token(client_id: str, client_secret: str) -> str:
    """Get token from Airthings API, valid 2 hours."""

    url = accounts_api_url + "token"
    data = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": ["read:device"],
    }
    response = requests.post(url, data=data)

    if response.status_code != 200:
        message = f"Failed to get token: Response {response.status_code} - {response.text}"
        logging.error(message)
        raise RuntimeError(message)

    data = response.json()
    access_token = data["access_token"]

    return access_token  # type: ignore


def get_device_list(access_token: str) -> list[dict]:
    """Get device list from Airthings API.

    Returns a list of dictionaries with the keys:
    """

    url = api_url + "devices"
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        message = f"Failed to get device list: Response {response.status_code} - {response.text}"
        logging.error(message)
        raise RuntimeError(message)

    data = response.json()
    device_list = data["devices"]

    return device_list  # type: ignore


def get_device_samples(
    access_token: str,
    device_id: str,
    datetime_start: datetime,
    datetime_end: datetime,
) -> dict[str, list]:
    """Get device samples from Airthings API.

    Returns a dictionary with the keys:
        - time: list[int]
        - xxx: list[Optional[float]]
    """

    data = None
    cursor = None

    logging.info(f"Getting samples for device {device_id} from {datetime_start} to {datetime_end}...")

    while True:
        new_data, cursor = get_device_samples_one_page(
            access_token=access_token,
            device_id=device_id,
            datetime_start=datetime_start,
            datetime_end=datetime_end,
            cursor=cursor,
        )

        if data is None:
            data = new_data
        else:
            data = append_data_samples(data, new_data)

        if cursor is None:
            break

        final_time = datetime.fromtimestamp(data["time"][-1])
        logging.info(f"Got data up to {final_time}. Continuing...")

    return data


def get_device_samples_one_page(
    access_token: str,
    device_id: str,
    datetime_start: datetime,
    datetime_end: datetime,
    cursor: Optional[str] = None,
) -> tuple[dict[str, list], Optional[str]]:
    """Get device samples from Airthings API.

    If cursor is None, get the first page of samples.
    Returns:
        - data: dict[str, list]
        - cursor: Optional[str]
    """

    url = f"{api_url}devices/{device_id}/samples"
    headers = {"Authorization": f"Bearer {access_token}"}
    params = {
        "start": utc_datetime_to_iso(datetime_start),
        "end": utc_datetime_to_iso(datetime_end),
    }
    if cursor is not None:
        params["cursor"] = cursor
    response = requests.get(url, headers=headers, params=params)

    if response.status_code != 200:
        message = f"Failed to get device samples: Response {response.status_code} - {response.text}"
        logging.error(message)
        raise RuntimeError(message)

    data = response.json()
    cursor = data.get("cursor", None)

    return data["data"], cursor


def append_data_samples(
    data: dict[str, list],
    new_data: dict[str, list],
):
    data = data.copy()

    for key in new_data:
        if key not in data:
            raise ValueError(f"Key {key} not found in original data.")
        data[key].extend(new_data[key])

    return data
