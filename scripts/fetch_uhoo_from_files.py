"""Fetch all minute-by-minute uHoo csv files in a directory.

The directory should have the structure:
└─ data
    ├── 2023.01
    │   ├── {device_name}_MinutebyMinuteData.csv
    │   └── ...
    └── ...
"""

import logging
import os
import sys

import inperso

SUFFIX = "_MinutebyMinuteData.csv"


def fetch_from_directory(dir_path: str):
    if not os.path.isdir(dir_path):
        raise FileNotFoundError(f"Directory not found: {dir_path}")

    retriever = inperso.data_acquisition.uhoo.UhooRetriever()

    for root, _, files in os.walk(dir_path):
        for file in files:
            if not file.endswith(SUFFIX):
                continue

            device_name = file.replace(SUFFIX, "")
            file_path = os.path.join(root, file)
            logging.info(f"Getting measurements for device {device_name} from {file_path}")
            retriever.fetch_from_file(file_path, device_name)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <directory>")
        sys.exit(1)

    dir_path = sys.argv[1]
    fetch_from_directory(dir_path)
