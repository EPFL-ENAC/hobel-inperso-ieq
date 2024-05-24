import logging

from . import config, data_acquisition, database, utils

__all__ = [
    "config",
    "data_acquisition",
    "database",
    "utils",
]

logging.basicConfig(level=logging.INFO)

__version__ = "0.0.0"
