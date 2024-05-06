import logging
import time
from datetime import datetime
from typing import Callable

import yaml


def load_yaml(path: str) -> dict:
    """Load a YAML file and return it as a dictionary."""

    with open(path, "r") as f:
        return yaml.safe_load(f)


def update_dict_nested(target: dict, update: dict) -> dict:
    """Update a dictionary with another dictionary, recursively."""

    for key, value in update.items():
        if isinstance(value, dict):
            current = target.get(key, {})
            target[key] = update_dict_nested(current, value)
        else:
            target[key] = value

    return target


def dict_ints_to_floats(dictionary: dict) -> dict:
    """Convert all integers in a dictionary to floats."""

    return {key: float(value) if isinstance(value, int) else value for key, value in dictionary.items()}


def utc_datetime_to_iso(d: datetime) -> str:
    """Convert a datetime object to an ISO 8601 string."""

    return d.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def iso_to_utc_datetime(s: str) -> datetime:
    """Convert an ISO 8601 string to a datetime object."""

    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def poll(maximum_retries: int, delay: float, fail_message: str):
    """Decorator to poll a function until it does not raise an exception."""

    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            for attempt in range(maximum_retries):
                try:
                    return func(*args, **kwargs)

                except Exception as e:
                    logging.error(f"{fail_message} (attempt {attempt + 1}/{maximum_retries}): {e}")
                    time.sleep(delay)

        return wrapper

    return decorator
