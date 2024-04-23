import logging
import multiprocessing as mp
from datetime import datetime, timedelta
from functools import partial

import requests

from inperso import config
from inperso.data_acquisition import uhoo


def request_period(
    token: str,
    url: str,
    serial: str,
    start: datetime,
    end: datetime,
) -> None:
    """Request data for a period, sent in multiple email."""

    start_list = []
    while start < end:
        start_list.append(start)
        start = add_one_month(start)

    request_partial = partial(request_one_month, token=token, url=url, serial=serial)
    with mp.Pool(mp.cpu_count()) as pool:
        successes = pool.map(request_partial, start_list)

    num_successes = sum(successes)
    logging.info(f"Requested {num_successes} samples")


def request_one_month(
    start: datetime,
    token: str,
    url: str,
    serial: str,
) -> bool:
    """Request one month of data, sent by email."""

    start = start.replace(hour=0, minute=0, second=0, microsecond=0)
    end = add_one_month(start) - timedelta(seconds=1)

    headers = {"Authorization": f"Bearer {token}"}
    data = {
        "serialNumber": serial,
        "fromDate": start.strftime("%Y-%m-%d %H:%M:%S"),
        "toDate": end.strftime("%Y-%m-%d %H:%M:%S"),
    }
    response = requests.post(url, headers=headers, data=data)
    logging.info(f"For request of {serial} from {start.strftime('%Y-%m-%d')}: status {response.status_code}")

    if response.status_code == 401:
        raise ValueError("Token expired.")

    return response.status_code == 200 or response.status_code == 504


def add_one_month(start: datetime) -> datetime:
    if start.month != 12:
        return start.replace(month=start.month + 1)
    else:
        return start.replace(year=start.year + 1, month=1)


token = uhoo.get_token(config.uhoo["client_id"])
url = "https://api.uhooinc.com/v1/wtvsRh/dataminute"
devices = uhoo.get_device_list(token)

datetime_start = datetime(2023, 1, 1)
datetime_end = datetime.now()
token = "cf3c61246860ab189653a8f7"  # get from dashboard network logs, not from the API. Update regularly.

for device in devices:
    logging.info(f"Requesting data for {device['deviceName']}")
    serial = device["serialNumber"]
    request_period(token, url, serial, datetime_start, datetime_end)
