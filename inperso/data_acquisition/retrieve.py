"""Get sensor data from APIs and store it in the database."""

import logging
import sys

from inperso.data_acquisition.airly import AirlyRetriever
from inperso.data_acquisition.airthings import AirthingsRetriever
from inperso.data_acquisition.qualtrics import QualtricsRetriever
from inperso.data_acquisition.uhoo import UhooRetriever


def main():
    retrievers = {
        "airly": AirlyRetriever,
        "airthings": AirthingsRetriever,
        "qualtrics": QualtricsRetriever,
        "uhoo": UhooRetriever,
    }

    if len(sys.argv) == 1:
        for name, retriever in retrievers.items():
            try:
                retriever().fetch_recent()
            except Exception as e:
                logging.error(f"Failed to fetch and store data from {name.capitalize()}: {e}")
                continue

    elif len(sys.argv) == 2:
        name = sys.argv[1]

        if name not in retrievers:
            print(f"retriever-type should be one of {list(retrievers.keys())}")
            sys.exit(1)

        retriever = retrievers[name]

        try:
            retriever().fetch_recent()
        except Exception as e:
            logging.error(f"Failed to fetch and store data from {name.capitalize()}: {e}")

    else:
        print(f"Usage: {sys.argv[0]} [retriever-type]")
        sys.exit(1)


if __name__ == "__main__":
    main()
