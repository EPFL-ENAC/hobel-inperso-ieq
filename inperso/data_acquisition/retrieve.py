"""Get sensor data from APIs and store it in the database."""

import datetime
import logging

from inperso.data_acquisition.airly import AirlyRetriever

# retrievers = [AirlyRetriever(), AirthingsRetriever(), UhooRetriever()]
retrievers = [AirlyRetriever()]


def main():
    # TODO: Get last stored datetime, up to now
    datetime_end = datetime.datetime.now(datetime.timezone.utc)
    datetime_start = datetime_end - datetime.timedelta(hours=1)

    for retriever in retrievers:
        try:
            retriever.fetch(
                datetime_start=datetime_start,
                datetime_end=datetime_end,
            )
            retriever.store()
        except Exception as e:
            logging.error(f"Failed to fetch and store data from {retriever.__class__.__name__}: {e}")
            continue


if __name__ == "__main__":
    main()
