import logging
from datetime import datetime, timedelta

import requests

from inperso import config
from inperso.data_acquisition.retriever import Retriever
from inperso.utils import dict_ints_to_floats, iso_to_utc_datetime

api_url = "https://airapi.airly.eu/v2/"


class AirlyRetriever(Retriever):
    @property
    def _measurement_name(self) -> str:
        return "airly"

    @property
    def _fetch_interval(self) -> timedelta:
        return timedelta(hours=config.airly["fetch_interval_hours"])

    def _fetch(
        self,
        datetime_start: datetime,
        datetime_end: datetime,
    ) -> None:
        """Retrieve data from the source and return it.

        Can only retrieve data for the last 24 hours.
        """

        installation_list = get_installation_list(config.airly["api_key"], config.airly["sponsor_name"])
        logging.info(f"Found {len(installation_list)} Airly installations for sponsor {config.airly['sponsor_name']}")

        for installation in installation_list:
            installation_id = installation["id"]
            city = installation["address"]["city"]
            latitude = installation["location"]["latitude"]
            longitude = installation["location"]["longitude"]

            try:
                logging.info(f"Getting measurements for installation {installation_id} in {city}")
                measurements = get_measurements(config.airly["api_key"], installation_id)
            except RuntimeError as e:
                logging.error(f"Failed to get measurements for installation {installation_id} in {city}: {e}")
                continue

            for measurement in measurements:
                sample_datetime_start = measurement["fromDateTime"]
                sample_datetime_end = measurement["tillDateTime"]
                midpoint_datetime = get_midpoint_datetime_from_strings(
                    sample_datetime_start,
                    sample_datetime_end,
                )
                fields = {}

                for value in measurement["values"]:
                    field_name = value["name"].lower()
                    field_value = value["value"]
                    fields[field_name] = field_value

                fields = dict_ints_to_floats(fields)
                self.add_write_query({
                    "measurement": self._measurement_name,
                    "tags": {
                        "device": installation_id,
                        "location": city,
                        "latitude": latitude,
                        "longitude": longitude,
                    },
                    "fields": fields,
                    "time": midpoint_datetime,
                })


def get_installation_list(api_key: str, sponsor_name: str) -> list[dict]:
    """Get installations from the Airly API."""

    url = api_url + "installations/nearest"
    headers = {
        "Accept": "application/json",
        "apikey": api_key,
    }
    params = {
        "lat": 46.519054,
        "lng": 6.566757,
        "maxDistanceKM": -1,
        "maxResults": -1,
    }
    response = requests.get(url, headers=headers, params=params)

    if response.status_code != 200:
        message = f"Failed to get installations list from Airly API: Response {response.status_code} - {response.text}"
        logging.error(message)
        raise RuntimeError(message)

    installation_list = response.json()
    logging.info(f"Found {len(installation_list)} Airly installations")
    installation_list = [i for i in installation_list if i["sponsor"]["name"] == sponsor_name]

    return installation_list


def get_measurements(api_key: str, installation_id: int) -> list[dict]:
    """Get day measurements from the Airly API.

    Returns a list of 24 dictionaries with the following structure: {
        "fromDateTime": str,
        "tillDateTime": str, one hour later
        "values": [
            {
                "name": str,
                "value": float,
            },
            ...
        ],
    }
    """

    url = api_url + "measurements/installation"
    headers = {
        "Accept": "application/json",
        "apikey": api_key,
    }
    params = {
        "installationId": installation_id,
    }
    response = requests.get(url, headers=headers, params=params)

    if response.status_code != 200:
        message = f"Failed to get measurements from Airly API: Response {response.status_code} - {response.text}"
        logging.error(message)
        raise RuntimeError(message)

    measurements = response.json()
    return measurements["history"]


def get_midpoint_datetime_from_strings(
    datetime_start_str: str,
    datetime_end_str: str,
) -> datetime:
    """Get the midpoint datetime ojbject from two datetimes iso strings."""

    datetime_start = iso_to_utc_datetime(datetime_start_str)
    datetime_end = iso_to_utc_datetime(datetime_end_str)
    return datetime_start + (datetime_end - datetime_start) / 2
