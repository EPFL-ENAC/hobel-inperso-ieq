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
    ) -> dict:
        """Retrieve data from the source and return it.

        Can only retrieve data for the last 24 hours.

        Returns a dictionary with the following structure: {
            "installation_id": {
                "city": str,
                "data": [
                    {
                        "fromDateTime": str,
                        "tillDateTime": str,
                        "values": [
                            {
                                "name": str,
                                "value": float,
                            },
                            ...
                        ],
                    },
                    ...
                ],
                "latitude": float,
                "longitude": float,
            },
            ...
        }
        """

        installation_list = get_installation_list(config.airly["api_key"], config.airly["sponsor_name"])
        logging.info(f"Found {len(installation_list)} Airly installations for sponsor {config.airly['sponsor_name']}")
        data = {}

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

            measurements = remove_fields_from_measurements(measurements, ["indexes", "standards"])
            data[installation_id] = {
                "city": city,
                "data": measurements,
                "latitude": latitude,
                "longitude": longitude,
            }

        return data

    def _get_line_queries(self) -> list[dict]:
        """Get line queries from stored data dictionary."""

        queries = []

        for installation_id, infos in self.data.items():
            city = infos["city"]
            latitude = infos["latitude"]
            longitude = infos["longitude"]
            measurements = infos["data"]

            for measurement in measurements:
                datetime_start = measurement["fromDateTime"]
                datetime_end = measurement["tillDateTime"]
                midpoint_datetime = get_midpoint_datetime_from_strings(datetime_start, datetime_end)
                fields = {}

                for value in measurement["values"]:
                    field_name = value["name"].lower()
                    field_value = value["value"]
                    fields[field_name] = field_value

                fields = dict_ints_to_floats(fields)
                queries.append({
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

        return queries


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


def remove_fields_from_measurements(
    measurements: list[dict],
    field_names: list[str],
) -> list[dict]:
    """Remove sets of computed fields from the measurements list.

    Useful to remove "indexes" and "standards" fields.
    """

    for measurement in measurements:
        for field_name in field_names:
            measurement.pop(field_name, None)

    return measurements


def get_midpoint_datetime_from_strings(
    datetime_start_str: str,
    datetime_end_str: str,
) -> datetime:
    """Get the midpoint datetime ojbject from two datetimes iso strings."""

    datetime_start = iso_to_utc_datetime(datetime_start_str)
    datetime_end = iso_to_utc_datetime(datetime_end_str)
    return datetime_start + (datetime_end - datetime_start) / 2
