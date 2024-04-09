import logging
from datetime import datetime
from typing import Optional

import requests

from inperso import config
from inperso.data_acquisition.retriever import Retriever
from inperso.utils import dict_ints_to_floats

accounts_api_url = "https://accounts-api.airthings.com/v1/"
api_url = "https://ext-api.airthings.com/v1/"


class AirthingsRetriever(Retriever):
    def _fetch(
        self,
        datetime_start: datetime,
        datetime_end: datetime,
    ) -> dict:
        """Retrieve data from the source and return it.

        Returns a dictionary of the form: {
            "device_name": {
                "data": {
                    "time": list[int],
                    "xxx": list[Optional[float]],
                },
                "type": str,
                "location": str,
            },
            "device_name_2": ...
        }
        """

        token = get_token(config.airthings["api_id"], config.airthings["api_key"])
        account_list = get_account_list(token)

        if len(account_list) == 0:
            logging.warning("No Airthings accounts found.")
            return {}

        logging.info(f"Found {len(account_list)} Airthings accounts.")
        data = {}

        for account in account_list:
            account_id = account["id"]

            device_list = get_device_list(token, account_id)
            logging.info(f"Found {len(device_list)} devices in account {account_id}.")

            for device in device_list:
                device_id = device["id"]

                device_data = get_device_samples(
                    access_token=token,
                    device_id=device_id,
                    datetime_start=datetime_start,
                    datetime_end=datetime_end,
                )

                device_name = device["segment"]["name"]
                device_type = device["deviceType"]
                device_location = device["location"]["name"]

                data[device_name] = {
                    "data": device_data,
                    "type": device_type,
                    "location": device_location,
                }

        return data

    def _get_line_queries(self) -> list[dict]:
        """Get line queries from stored data dictionary."""

        queries = []

        for device_name, device_info in self.data.items():
            device_data = device_info["data"]
            device_type = device_info["type"]
            device_location = device_info["location"]

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

                queries.append({
                    "measurement": "airthings",
                    "tags": {
                        "device": device_name,
                        "type": device_type,
                        "location": device_location,
                    },
                    "fields": fields,
                    "time": timestamp,
                })

        return queries


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


def get_account_list(access_token: str) -> list[dict]:
    """Get account list from Airthings API.

    Returns a list of dictionaries with the keys:
        - id: str
        - name: str
    """

    url = api_url + "accounts"
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        message = f"Failed to get account list: Response {response.status_code} - {response.text}"
        logging.error(message)
        raise RuntimeError(message)

    data = response.json()
    account_list = data["accounts"]

    return account_list


def get_device_list(access_token: str, account_id: str) -> list[dict]:
    """Get device list from Airthings API.

    Returns a list of dictionaries with the keys:
    """

    url = api_url + "devices"
    headers = {"Authorization": f"Bearer {access_token}"}
    params = {
        "accountId": account_id,
    }
    response = requests.get(url, headers=headers, params=params)

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
    start = datetime_start.isoformat()
    end = datetime_end.isoformat()
    headers = {"Authorization": f"Bearer {access_token}"}
    params = {
        "start": start,
        "end": end,
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
