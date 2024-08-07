[![Project Status](https://img.shields.io/badge/status-under%20development-yellow)](https://github.com/EPFL-ENAC/hobel-inperso-ieq)

# 🌡 HOBEL InPerso IEQ

The project aims to advance the knowledge of indoor environmental quality (IEQ) assessment in residential and educational buildings in Europe, develop an improved rating system for IEQ assessment, and understand the impact of building retrofits on Indoor environmental quality and occupants’ comfort.


# 📥 Installation

## Requirements

- Python 3.10 minimum


## For users

```
git clone https://github.com/EPFL-ENAC/hobel-inperso-ieq.git
cd hobel-inperso-ieq
pip install .
```


## For developers

```
git clone git@github.com:EPFL-ENAC/hobel-inperso-ieq.git
cd hobel-inperso-ieq
pip install -e .[dev]
```


# 👨‍💻 Fetching data from the database

First, export the following environment variables:

- `INFLUX_BUCKET=bucket`
- `INFLUX_HOST` (such as `http://db.com:8086`)
- `INFLUX_ORG=enac`
- `INFLUX_TOKEN`

This can be done by putting the variables in an `.env` file and then running

```
export $(cat .env)
```


## Sensor data

In a Python script or notebook you can use the `fetch` function to retrieve data from the database:

```
from datetime import datetime
import pandas as pd
from inperso import fetch

data = fetch(
    datetime_start = datetime(2024, 1, 1),
    datetime_end = datetime.now(),
    frequency = "1h",
    window_size = "1d",
    brands = ["airly", "airthings", "uhoo"],
    fields = ["pressure"],
    room = ["bedroom", "kitchen"],
    # ...
)

df = pd.DataFrame(data)
```

Run `help(fetch)` to get more info on the available filters.


## Survey data

To fetch survey data, use the `fetch_surveys` function:

```
import pandas as pd
from inperso import fetch_surveys

data = fetch_surveys(
    surveys = ["survey1", "survey2"],
    # ...
)

df = pd.DataFrame(data)
```

Use the `get_survey_names` function to get the list of available surveys. It is also possible to filter the surveys by date using the `datetime_start` and `datetime_end` arguments.


# ⛏️ Populating the database with data from the APIs

Export the following environment variables:

- `AIRLY_API_KEY`
- `AIRTHINGS_API_ID`
- `AIRTHINGS_API_KEY`
- `UHOO_CLIENT_ID`
- `QUALTRICS_API_KEY`
- `INFLUX_BUCKET=bucket`
- `INFLUX_HOST`
- `INFLUX_ORG=enac`
- `INFLUX_TOKEN`

This can be done by putting the variables in an `.env` file and then running

```
export $(cat .env)
```


## Command line usage

To retrieve all the latest samples for all sensors and surveys and store them in the database, run in your terminal:

```
inperso-retrieve
```


## Script usage

### Fetch recent data

To manually retrieve recent samples in a Python shell or notebook, run the following script:

```
import inperso

retriever = inperso.data_acquisition.AirlyRetriever()
retriever.fetch_recent()
```

Replace `AirlyRetriever` by the desired sensor or survey type, taken from:

- `AirlyRetriever`
- `AirthingsRetriever`
- `QualtricsRetriever`
- `UhooRetriever`


### Fetch data within a time interval

To fetch samples between two particular dates, run:

```
import inperso
from datetime import datetime, timedelta, timezone

datetime_start = datetime(2024, 1, 2, 0, 0, 0, tzinfo=timezone.utc)
datetime_end = datetime_start + timedelta(days=1)
retriever = inperso.data_acquisition.AirlyRetriever()
retriever.fetch(datetime_start, datetime_end)
```


### Fetch data from a file

To fetch samples from a file, run:

```
import inperso

retriever = inperso.data_acquisition.AirlyRetriever()
retriever.fetch_from_file("path/to/file.csv")
```


## 🛢️ Steps to populate the database

To fill the database with historical data, follow these steps for each kind of sensor.

### Airly

- On the Airly Dashboard website, go to the Report Generator tab and export a hour-by-hour csv file.
- Follow the `Fetch data from a file` instructions.


### Airthings

- Follow the `Fetch data within a time interval` instructions.


### Qualtrics

- Follow the `Fetch data within a time interval` instructions.


### uHoo

- Use `scripts/request_uhoo_minute_data.py` to request minute-by-minute csv files. The token must be retrieved from the uHoo Dashboard (using inspector tools).
- Follow the `Fetch data from a file` instructions. If multiple files should be processed, use `scripts/fetch_uhoo_from_files.py`.


# ✅ Run tests

```
pytest
```


# 🩺 Run code checks

```
pre-commit run --all-files
```
