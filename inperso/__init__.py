import logging

from . import config, data_acquisition, database, utils
from .fetch import fetch

__all__ = [
    "config",
    "data_acquisition",
    "database",
    "fetch",
    "utils",
]

logging.basicConfig(level=logging.INFO)

__version__ = "0.0.0"
