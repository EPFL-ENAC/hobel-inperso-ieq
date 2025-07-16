[![Project Status](https://img.shields.io/badge/status-under%20development-yellow)](https://github.com/EPFL-ENAC/hobel-inperso-ieq)

# 🌡 HOBEL InPerso IEQ

The project aims to advance the knowledge of indoor environmental quality (IEQ) assessment in residential and educational buildings in Europe, develop an improved rating system for IEQ assessment, and understand the impact of building retrofits on Indoor environmental quality and occupants’ comfort.

All retrieved data can be displayed on the [InPerso IEQ Dashboard](https://inperso-ieq-dev.epfl.ch/) (authenticated access).


# 📥 Installation

## Requirements

- Python 3.10 minimum


## For users

```bash
pip install git+https://github.com/EPFL-ENAC/hobel-inperso-ieq.git
```


## For developers

```bash
git clone git@github.com:EPFL-ENAC/hobel-inperso-ieq.git
cd hobel-inperso-ieq
pip install -e .[dev]
```


# 👨‍💻 Fetching data from the database

At the root of your project, create a `.env` file with the following content:

```bash
INFLUX_HOST=https://inperso-ieq-db-dev.epfl.ch:443
INFLUX_TOKEN=your_token
```

Alternatively, you can set the environment variables directly in your script or notebook:

```python
import inperso

inperso.config.db["host"] = "https://inperso-ieq-db-dev.epfl.ch:443"
inperso.config.db["token"] = "your_token"
```


## Sensor data

In a Python script or notebook you can use the `fetch` function to retrieve data from the database, potentially resampled:

```python
from datetime import datetime
import pandas as pd  # Optional, if you want to convert the data into a DataFrame
import inperso

data = inperso.fetch(
    datetime_start = datetime(2024, 1, 1),
    datetime_end = datetime.now(),
    frequency = "1h",
    window_size = "1d",
    brands = ["airly", "airthings", "uhoo"],
    fields = ["pressure"],
    room = ["bedroom", "kitchen"],
    # ...
)

df = pd.DataFrame(data)  # Optional
```

Run `help(inperso.fetch)` to get more info on the available filters.


## Survey data

To fetch survey data, use the `fetch_surveys` function:

```python
import pandas as pd  # Optional, if you want to convert the data into a DataFrame
import inperso

data = inperso.fetch_surveys(
    surveys = ["survey1", "survey2"],
    # ...
)

df = pd.DataFrame(data)  # Optional
```

Use the `inperso.get_survey_names()` function to get the list of available surveys. It is also possible to filter the surveys by date using the `datetime_start` and `datetime_end` arguments.


# ⛏️ Populating the database with data from the APIs

At the root of your project, create a `.env` file with the following variables:

```bash
AIRLY_API_KEY=...
AIRTHINGS_API_ID=...
AIRTHINGS_API_KEY=...
UHOO_CLIENT_ID=...
QUALTRICS_API_KEY=...
INFLUX_BUCKET=bucket
INFLUX_HOST=...
INFLUX_ORG=enac
INFLUX_TOKEN=...
```


## Command line usage

To retrieve all the latest samples for all sensors and surveys and store them in the database, run in your terminal:

```bash
inperso-retrieve
```

You can also selectively retrieve data for a specific sensor or survey type:

```bash
inperso-retrieve airly
```

Replace `airly` by the desired sensor or survey type, taken from:

- `airly`
- `airthings`
- `qualtrics`
- `uhoo`


## Script usage

### Fetch recent data

To manually retrieve recent samples in a Python shell or notebook, run the following script:

```python
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

```python
import inperso
from datetime import datetime, timedelta, timezone

datetime_start = datetime(2024, 1, 2, 0, 0, 0, tzinfo=timezone.utc)
datetime_end = datetime_start + timedelta(days=1)
retriever = inperso.data_acquisition.AirlyRetriever()
retriever.fetch(datetime_start, datetime_end)
```


### Fetch data from a file

To fetch samples from a file, run:

```python
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

```bash
pytest
```


# 🩺 Run code checks

```bash
pre-commit run --all-files
```
