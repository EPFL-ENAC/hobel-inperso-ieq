"""This script generates definitions for custom Grafana variables based on a
CSV file of tags.
"""

import csv

filepath = "data/tags.csv"
device_name_column = 1


header = []
data = []

with open(filepath, mode="r") as file:
    reader = csv.reader(file, delimiter=";")
    header = next(reader)

    for row in reader:
        data.append(row)


for key_index in range(len(header)):
    if key_index == device_name_column:
        continue

    key = header[key_index]
    values_and_devices = {}  # type: ignore

    for row in data:
        device_name = row[device_name_column]
        value = row[key_index]

        if value == "":
            continue

        if value not in values_and_devices:
            values_and_devices[value] = []

        values_and_devices[value].append(device_name)

    values_and_devices = dict(sorted(values_and_devices.items()))

    print(f"\nVariable: {key}\n")
    grafana_values = ", ".join([f"{value} : {'|'.join(devices)}" for value, devices in values_and_devices.items()])
    print(grafana_values)
