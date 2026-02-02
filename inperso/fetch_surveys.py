"""Function to manually fetch survey data from the database"""

import logging
from datetime import datetime
from functools import cache
from typing import Optional

from inperso import config
from inperso.database.read import get_datetime_filter, query

SURVEY_MEASUREMENT = "qualtrics"


def fetch_surveys(
    surveys: Optional[list[str]] = None,
    datetime_start: Optional[datetime] = None,
    datetime_end: Optional[datetime] = None,
) -> list[dict]:
    """Fetch survey data from the database.

    Args:
        surveys (list[str]): List of surveys to retrieve data from.
            Defaults to None, which raises an error and lists the valid surveys.
        datetime_start (datetime, optional): Start of the time range.
            Defaults to None, which retrieve data from timestamp 0.
        datetime_end (datetime, optional): End of the time range.
            Defaults to None, which retrieve data until now.

    Returns:
        list[dict]: List of dictionaries containing the data, with the keys:
            - "survey" (str)
            - "time" (datetime)
            - "response_id" (str)
            - "latitude" (float | None)
            - "longitude" (float | None)
            - "question" (str)
            - "answer" (any)
    """
    query_str = f'from(bucket:"{config.db["bucket"]}")'
    query_str += get_datetime_filter(datetime_start, datetime_end)
    query_str += f'|> filter(fn: (r) => r["_measurement"] == "{SURVEY_MEASUREMENT}")'
    query_str += _get_surveys_filter(surveys)

    logging.info("Running the query:\n" + query_str.replace("|>", "\n|>"))
    result = query(query_str)
    values = [record.values for table in result for record in table.records]

    # Only keep relevant fields
    values = [
        {
            "survey": record["survey"],
            "time": record["_time"],
            "response_id": record["response_id"],
            "latitude": record.get("latitude", None),
            "longitude": record.get("longitude", None),
            "question": record["_field"],
            "answer": record["_value"],
        }
        for record in values
    ]

    return values


def _get_surveys_filter(surveys: Optional[list[str]] = None) -> str:
    if surveys is None or len(surveys) == 0:
        raise ValueError(f"Must provide a list of surveys to fetch data from. Must choose from: {get_survey_names()}.")

    valid_surveys = get_survey_names()
    invalid_surveys = set(surveys) - set(valid_surveys)

    if invalid_surveys:
        raise ValueError(f"Invalid surveys: {invalid_surveys}. Must choose from: {valid_surveys}.")

    # surveys = [re.escape(survey) for survey in surveys]
    # return f'|> filter(fn: (r) => r["survey"] =~ /({"|".join(surveys)})/)'
    conditions = [f'r["survey"] == "{survey}"' for survey in surveys]
    return f"|> filter(fn: (r) => {' or '.join(conditions)})"


@cache
def get_survey_names() -> list[str]:
    """Get the list of survey names from the database."""

    result = query(
        f"""
        import "influxdata/influxdb/schema"
        schema.tagValues(
            bucket: "{config.db["bucket"]}",
            tag: "survey",
            predicate: (r) => r._measurement == "{SURVEY_MEASUREMENT}",
            start: 0,
            stop: now(),
        )
    """
    )
    values = [record.values["_value"] for table in result for record in table.records]
    return values
