import logging
import threading
from datetime import datetime, timedelta

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

    while start < end:
        send_and_forget(lambda: request_one_month(token, url, serial, start))
        start = add_one_month(start)


def request_one_month(
    token: str,
    url: str,
    serial: str,
    start: datetime,
) -> None:
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
    logging.info(f"For request of {serial} from {start.strftime('%Y-%m-%d')}, response: {response.text}")


def add_one_month(start: datetime) -> datetime:
    if start.month != 12:
        return start.replace(month=start.month + 1)
    else:
        return start.replace(year=start.year + 1, month=1)


def send_and_forget(func):
    threading.Thread(target=func).start()


token = uhoo.get_token(config.uhoo["client_id"])
url = "https://api.uhooinc.com/v1/wtvsRh/dataminute"
devices = uhoo.get_device_list(token)

datetime_start = datetime(2023, 1, 1)
datetime_end = datetime.now()

for device in devices:
    serial = device["serialNumber"]
    request_period(token, url, serial, datetime_start, datetime_end)
