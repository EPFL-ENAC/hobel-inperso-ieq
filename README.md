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


# 🏎 Usage

Export the following environment variables:

- `AIRLY_API_KEY`
- `AIRTHINGS_API_ID`
- `AIRTHINGS_API_KEY`
- `UHOO_CLIENT_ID`
- `QUALTRICS_API_KEY`
- `INFLUX_HOST`
- `INFLUX_PORT`
- `INFLUX_TOKEN`

This can be done by putting the variables in an `.env` file and then running

```
export $(cat .env)
```


## Command line usage

To retrieve all the latest samples for all sensors and surveys, run in your terminal:

```
inperso-retrieve
```


## Script usage

To manually retrieve recent samples in a Python shell or notebook, run the following script:

```
import inperso

retriever = inperso.data_acquisition.AirlyRetriever()
retriever.fetch_recent_and_store()
```

Replace `AirlyRetriever` by the desired sensor or survey type, taken from:

- `AirlyRetriever`
- `AirthingsRetriever`
- `QualtricsRetriever`
- `UhooRetriever`

To fetch samples between two particular dates, run:

```
import inperso
from datetime import datetime, timedelta, timezone

datetime_start = datetime(2024, 1, 2, 0, 0, 0, tzinfo=timezone.utc)
datetime_end = datetime_start + timedelta(days=1)
retriever = inperso.data_acquisition.AirlyRetriever()
retriever.fetch_and_store(datetime_start, datetime_end)
```


# ✅ Run tests

```
pytest
```


# 🩺 Run code checks

```
pre-commit run --all-files
```
