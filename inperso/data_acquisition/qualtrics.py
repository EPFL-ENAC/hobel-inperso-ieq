import io
import json
import logging
import time
import zipfile
from datetime import datetime
from typing import Optional

import requests

from inperso import config
from inperso.data_acquisition.retriever import Retriever

api_url = "https://sjc1.qualtrics.com/API/v3/"


class AirlyRetriever(Retriever):
    def _fetch(
        self,
        datetime_start: datetime,
        datetime_end: datetime,
    ) -> dict:
        """Retrieve data from the source and return it."""

        data = {}
        return data

    def _get_line_queries(self) -> list[dict]:
        """Get line queries from stored data dictionary."""

        queries = []
        return queries


def get_survey_list(api_key: str) -> list[dict]:
    """Get list of surveys from Qualtrics API.

    Returns a list of dictionaries with the keys:
        - id: str
        - name: str
        - lastModified: str, ISO 8601 date
        - creationDate: str, ISO 8601 date
        - isActive: bool
    """

    url = api_url + "surveys"
    headers = {
        "X-API-TOKEN": api_key,
    }
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        message = f"Failed to get list of surveys from Qualtrics API: Response {response.status_code} - {response.text}"
        logging.error(message)
        raise RuntimeError(message)

    data = response.json()
    return data["result"]["elements"]


def get_survey(api_key: str, survey_id: str) -> dict:
    """Get survey details from Qualtrics API.

    Returns a dictionary with the structure (non exhaustive): {
        "id": str,
        "name": str,
        "questions": {
            id: {
                "questionText": str,
            }
        }
    }
    """

    url = api_url + f"surveys/{survey_id}"
    headers = {
        "X-API-TOKEN": api_key,
    }
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        message = f"Failed to get survey details from Qualtrics API: Response {response.status_code} - {response.text}"
        logging.error(message)
        raise RuntimeError(message)

    data = response.json()
    return data["result"]


def get_responses(
    api_key: str,
    survey_id: str,
    datetime_start: datetime,
    datetime_end: datetime,
) -> list:
    """Get responses for one survey from Qualtrics API."""

    logging.info(f"Getting responses for survey {survey_id} from {datetime_start} to {datetime_end}")

    progress_id = request_response_export(
        api_key=api_key,
        survey_id=survey_id,
        datetime_start=datetime_start,
        datetime_end=datetime_end,
    )

    logging.info(f"Response export requested. Progress ID: {progress_id}")
    logging.info("Polling for response export file...")

    waiting_time = 0
    file_id = None

    while True:
        file_id = get_response_export_file_id(api_key, survey_id, progress_id)
        if file_id is not None:
            break

        if waiting_time >= config.qualtrics["max_wait_get_response"]:
            logging.error("Could not get responses from Qualtrics API: Timeout")
            return []

        time.sleep(config.qualtrics["polling_interval_get_response"])
        waiting_time += config.qualtrics["polling_interval_get_response"]

    logging.info(f"Response export file ready. File ID: {file_id}")

    return get_response_export(api_key, survey_id, file_id)


def request_response_export(
    api_key: str,
    survey_id: str,
    datetime_start: datetime,
    datetime_end: datetime,
) -> str:
    """Request a response export from Qualtrics API."""

    url = api_url + f"surveys/{survey_id}/export-responses"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "X-API-TOKEN": api_key,
    }
    data = {
        "format": "json",
        "startDate": utc_datetime_to_iso(datetime_start),
        "endDate": utc_datetime_to_iso(datetime_end),
    }
    response = requests.post(url, headers=headers, data=json.dumps(data))

    if response.status_code != 200:
        message = (
            f"Failed to request response export from Qualtrics API: Response {response.status_code} - {response.text}"
        )
        logging.error(message)
        raise RuntimeError(message)

    data = response.json()
    progress_id = data["result"]["progressId"]
    return progress_id


def get_response_export_file_id(
    api_key: str,
    survey_id: str,
    progress_id: str,
) -> Optional[str]:
    """Check if a response export is finished and return the file ID if it is."""

    url = api_url + f"surveys/{survey_id}/export-responses/{progress_id}"
    headers = {
        "Accept": "application/json",
        "X-API-TOKEN": api_key,
    }
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        message = f"Failed to get response export progress from Qualtrics API: Response {response.status_code} - {response.text}"
        logging.error(message)
        raise RuntimeError(message)

    data = response.json()
    status = data["result"]["status"]

    if status == "failed":
        message = f"Response export failed: {data['result']['errorMessage']}"
        logging.error(message)
        raise RuntimeError(message)

    if status == "complete":
        return data["result"]["fileId"]

    return None


def get_response_export(
    api_key: str,
    survey_id: str,
    file_id: str,
) -> list:
    """Get the response export file from Qualtrics API."""

    url = api_url + f"surveys/{survey_id}/export-responses/{file_id}/file"
    headers = {
        "Accept": "application/json",
        "X-API-TOKEN": api_key,
    }
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        message = (
            f"Failed to get response export file from Qualtrics API: Response {response.status_code} - {response.text}"
        )
        logging.error(message)
        raise RuntimeError(message)

    if response.headers["Content-Type"] != "application/zip":
        message = "Failed to get response export file from Qualtrics API: Unexpected content type. Expected zip."
        logging.error(message)
        raise RuntimeError(message)

    with zipfile.ZipFile(io.BytesIO(response.content)) as zip_file:
        file_name = zip_file.namelist()[0]
        with zip_file.open(file_name) as file:
            data = json.load(file)

    return data["responses"]


def utc_datetime_to_iso(d: datetime) -> str:
    """Convert a datetime object to an ISO 8601 string."""

    return d.replace(microsecond=0).isoformat().replace("+00:00", "Z")
