"""This script generates definitions for custom Grafana variables based on a
CSV file of tags.
"""

from inperso.tags import tags

for key, values_and_devices in tags.items():
    print(f"\nVariable: {key}\n")
    grafana_values = ", ".join([f"{value} : {'|'.join(devices)}" for value, devices in values_and_devices.items()])
    print(grafana_values)
