"""Get sensor data from APIs and store it in the database."""

from inperso.data_acquisition.airly import AirlyRetriever
from inperso.data_acquisition.airthings import AirthingsRetriever
from inperso.data_acquisition.uhoo import UhooRetriever


retrievers = [AirlyRetriever(), AirthingsRetriever(), UhooRetriever()]


def main():
    for retriever in retrievers:
        retriever.retrieve()
        retriever.store()


if __name__ == "__main__":
    main()
