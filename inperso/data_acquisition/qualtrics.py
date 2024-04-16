import io
import json
import logging
import time
import zipfile
from datetime import datetime, timedelta
from typing import Optional

import requests

from inperso import config
from inperso.data_acquisition.retriever import Retriever

api_url = "https://sjc1.qualtrics.com/API/v3/"


class QualtricsRetriever(Retriever):
    @property
    def _measurement_name(self) -> str:
        return "qualtrics"

    @property
    def _fetch_interval(self) -> timedelta:
        return timedelta(hours=config.qualtrics["fetch_interval_hours"])

    def _fetch(
        self,
        datetime_start: datetime,
        datetime_end: datetime,
    ) -> dict:
        """Retrieve data from the source and return it.

        Returns a dictionary with the structure: {
            response_id: {
                "survey": str,
                "data": {
                    "recordedDate": str, ISO 8601 date
                    "locationLatitude": str,
                    "locationLongitude": str,
                    "QIDxxx": int or list[int],
                    "QIDxxx_TEXT": str,
                }
            }
        }
        """

        survey_list = get_survey_list(config.qualtrics["api_key"])
        logging.info(f"Found {len(survey_list)} Qualtrics surveys")
        data = {}

        for survey in survey_list:
            survey_id = survey["id"]
            survey_name = survey["name"]

            try:
                responses = get_responses(
                    api_key=config.qualtrics["api_key"],
                    survey_id=survey_id,
                    datetime_start=datetime_start,
                    datetime_end=datetime_end,
                )
            except RuntimeError as e:
                logging.error(f"Failed to get responses for survey {survey_id}: {e}")
                continue

            logging.info(f'Got {len(responses)} responses for survey "{survey_name}"')

            for response in responses:
                response_id = response["responseId"]
                data[response_id] = {
                    "survey": survey_name,
                    "data": response["values"],
                }

        return data

    def _get_line_queries(self) -> list[dict]:
        """Get line queries from stored data dictionary."""

        queries = []

        for response_info in self.data.values():
            survey = response_info["survey"]
            data = response_info["data"]
            date = datetime.fromisoformat(data["recordedDate"].replace("Z", "+00:00"))
            answers = parse_answers(data)

            tags = {
                "survey": survey,
            }
            if "locationLatitude" in data:
                tags["latitude"] = float(data["locationLatitude"])
            if "locationLongitude" in data:
                tags["longitude"] = float(data["locationLongitude"])

            queries.append({
                "measurement": self._measurement_name,
                "tags": tags,
                "fields": answers,
                "time": date,
            })

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
) -> list[dict]:
    """Get responses for one survey from Qualtrics API.

    Returns a list of dictionaries with the structure (non exhaustive): {
        "responseId": str,
        "values": {
            "recordedDate": str, ISO 8601 date
            "locationLatitude": str,
            "locationLongitude": str,
            "QIDxxx": int or list[int],
            "QIDxxx_TEXT": str,
        }
    }
    """

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
    logging.info("Downloading response export file...")

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
    progress_id = data["result"]["progressId"]  # type: ignore
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
) -> list[dict]:
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


def parse_answers(data: dict) -> dict:
    """Parse answers from a Qualtrics response data dictionary.

    Keep all the keys starting with "QID". If value is a list of integers (multiple choice), create "QIDx_y" boolean entries.
    Ex: QID12: [3, 4, 6] -> QID12_3: True, QID12_4: True, QID12_6: True
    """

    answers = {}

    for key, value in data.items():
        if not key.startswith("QID"):
            continue

        if isinstance(value, list):
            for choice in value:
                answers[f"{key}_{choice}"] = True
        else:
            answers[key] = value

    return answers
