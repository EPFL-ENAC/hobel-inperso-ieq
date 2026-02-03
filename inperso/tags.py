"""Get lists of devices associated to tags from a CSV file of tags."""

import csv
import os

package_path = os.path.dirname(os.path.abspath(__file__))
filepath = os.path.join(package_path, "data", "tags.csv")
device_name_column = 1


tags = {}
unit_numbers: dict[str, str] = {}
dcs: dict[str, str] = {}


header = []
data = []

with open(filepath, mode="r") as file:
    reader = csv.reader(file, delimiter=",")
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
    tags[key] = values_and_devices


for unit_number, device_names in tags.get("Unit number", {}).items():
    for device_name in device_names:
        unit_numbers[device_name] = unit_number

unit_numbers = dict(sorted(unit_numbers.items()))


for dc, device_names in tags.get("DC", {}).items():
    for device_name in device_names:
        dcs[device_name] = dc

dcs = dict(sorted(dcs.items()))
