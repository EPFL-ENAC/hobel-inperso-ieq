[![Project Status](https://img.shields.io/badge/status-under%20development-yellow)](https://github.com/EPFL-ENAC/hobel-inperso-ieq)

# 🌡 HOBEL InPerso IEQ

The project aims to advance the knowledge of indoor environmental quality (IEQ) assessment in residential and educational buildings in Europe, develop an improved rating system for IEQ assessment, and understand the impact of building retrofits on Indoor environmental quality and occupants’ comfort.

All retrieved data can be displayed on the [InPerso IEQ Dashboard](https://inperso-ieq-dev.epfl.ch/) (authenticated access).


# 📥 Installation

## Requirements

- Python 3.11 minimum


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


## ATLAS scores and index

Similarly, to fetch ATLAS scores and index, use the `fetch_atlas_scores` and `fetch_atlas_index` functions:

```python
from datetime import datetime
import pandas as pd  # Optional, if you want to convert the data into a DataFrame
import inperso

data_scores = inperso.fetch_atlas_scores(
    datetime_start = datetime(2024, 1, 1),
    datetime_end = datetime.now(),
    # frequency = "1h",
    # window_size = "1d",
    # unit_numbers = ["1-25", "1-26"],
    # fields = ["ch2o", "co"],
    # dc = ["1", "2" , "3"],
)

data_index = inperso.fetch_atlas_index(
    datetime_start = datetime(2024, 1, 1),
    datetime_end = datetime.now(),
    # frequency = "1h",
    # window_size = "1d",
    # unit_numbers = ["1-25", "1-26"],
    # categories = ["atlas_index", "iaq", "lux", "noise", "thermal"],
    # dc = ["1", "2" , "3"],
)

df_scores = pd.DataFrame(data_scores)  # Optional
df_index = pd.DataFrame(data_index)    # Optional
```


### Compute the scores from an existing DataFrame

To compute the ATLAS scores from an existing DataFrame, without fetching from the database, use the `inperso.atlas_index.scores` module. The DataFrame needs the columns `time` (UTC), `brand` (`airly`, `airthings`, or `uhoo`), `device`, `field`, and `value`:

```python
import pandas as pd
from inperso.atlas_index.scores import compute_scores_inperso

df = pd.DataFrame(data)  # Or any DataFrame with the expected columns

df_scores = compute_scores_inperso(df, write_to_db=False)
```

Use `compute_scores` with a `ScoreContext` to choose the building type, cooling type, and heating season:

```python
from inperso.atlas_index.scores import ScoreContext, compute_scores

context = ScoreContext(
    building_type = "residential",   # or "school"
    cooling_type = "natural",        # or "mechanical"
    heating_season = "mixed",        # or "heating", "non-heating"
    heating_season_start = "11/01",  # required when heating_season is "mixed"
    heating_season_end = "03/31",
    occupancy_start_hour = 8,        # optional, overrides the config default
    occupancy_end_hour = 18,
)

df_scores, fallback_note = compute_scores(df, context)
```

Both functions return a DataFrame with the columns `time`, `field`, `unit_number`, and `score`.

Expected `field` names, descriptions, and units:

| Field | Description | Unit |
| :--- | :--- | :--- |
| `temperature` | Indoor air temperature | °C |
| `outdoor_temperature` | Outdoor air temperature, used for the natural cooling adjustment | °C |
| `co2` | Carbon dioxide concentration | ppm |
| `humidity` | Relative humidity | % |
| `pm25` | PM2.5 mass concentration | µg/m3 |
| `pm10` | PM10 mass concentration | µg/m3 |
| `o3` | Ozone mass concentration | µg/m3 |
| `no2` | Nitrogen dioxide mass concentration | µg/m3 |
| `so2` | Sulfur dioxide mass concentration | µg/m3 |
| `co` | Carbon monoxide mass concentration | mg/m3 |
| `ch2o` | Formaldehyde mass concentration | µg/m3 |
| `rn` | Radon activity concentration | Bq/m3 |
| `light_percent_day` | Part of the daytime with light above the light threshold | % |
| `light_percent_night` | Part of the night with light above the light threshold | % |
| `light` | Illuminance, scored for school contexts during occupied periods | lux |
| `occupancy` | Occupancy state, decides the occupied periods for the school light scores | - |
| `sla_day` | A-weighted sound level during the day | dB(A) |
| `sla_night` | A-weighted sound level during the night | dB(A) |
| `reverberation_time` | Reverberation time, scored for school contexts | s |

The `value` column must use the units of the table. The `sla_day`, `sla_night`, `light_percent_day`, and `light_percent_night` fields are derived from `sla` and `light` data by the preprocessing functions of `inperso.atlas_index.preprocessing`.

To compute the ATLAS index from the scores, use the `inperso.atlas_index.index` module:

```python
from inperso.atlas_index.index import compute_index_from_scores

df_index = compute_index_from_scores(df_scores)
```

`df_scores` needs the columns `time`, `field`, `unit_number`, and `score`. The result contains `time`, `unit_number`, the category scores (`iaq`, `thermal`, `lux`, `noise`), and the `atlas_index`, the weighted geometric mean of the available category scores. Categories without data are skipped and the weights are renormalized.


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
