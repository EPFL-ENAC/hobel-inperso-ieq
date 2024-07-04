import logging

from . import config, data_acquisition, database, utils
from .fetch import fetch
from .fetch_surveys import fetch_surveys, get_survey_names

__all__ = [
    "config",
    "data_acquisition",
    "database",
    "fetch",
    "fetch_surveys",
    "get_survey_names",
    "utils",
]

logging.basicConfig(level=logging.INFO)

__version__ = "0.0.0"
