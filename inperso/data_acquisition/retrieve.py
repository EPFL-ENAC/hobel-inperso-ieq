"""Get sensor data from APIs and store it in the database."""

import logging

from inperso.data_acquisition.airly import AirlyRetriever
from inperso.data_acquisition.airthings import AirthingsRetriever
from inperso.data_acquisition.qualtrics import QualtricsRetriever
from inperso.data_acquisition.uhoo import UhooRetriever


def main():
    retrievers = [
        AirlyRetriever(),
        AirthingsRetriever(),
        QualtricsRetriever(),
        UhooRetriever(),
    ]

    for retriever in retrievers:
        try:
            retriever.fetch_recent()
        except Exception as e:
            logging.error(f"Failed to fetch and store data from {retriever.__class__.__name__}: {e}")
            continue


if __name__ == "__main__":
    main()
