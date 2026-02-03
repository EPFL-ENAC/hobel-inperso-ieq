from datetime import datetime

import pandas as pd

from inperso import config
from inperso.fetch import fetch

DATAFRAME_COLUMNS = ["time", "brand", "device", "field", "value"]


def preprocess_measurements(datetime_start: datetime, datetime_end: datetime) -> pd.DataFrame:
    """Retrieve and preprocess the measurements from the database."""

    data = fetch(
        datetime_start=datetime_start,
        datetime_end=datetime_end,
        frequency="1h",
        window_size="1h",
    )

    if len(data) == 0:
        return pd.DataFrame(columns=DATAFRAME_COLUMNS)

    df = pd.DataFrame(data)
    df = convert_units(df)
    df = compute_light_percent(datetime_start, datetime_end, df)
    df = compute_sla(df)

    return df


def convert_units(df: pd.DataFrame) -> pd.DataFrame:
    unit_conversion_factors = config.atlas_index["unit_conversion_factors"]

    for brand, field_factors in unit_conversion_factors.items():
        for field, factor in field_factors.items():
            mask = (df["brand"] == brand) & (df["field"] == field)
            df.loc[mask, "value"] = df.loc[mask, "value"] * factor

    return df


def compute_light_percent(datetime_start: datetime, datetime_end: datetime, df: pd.DataFrame) -> pd.DataFrame:
    config_light_percent = config.atlas_index["light_percent"]
    day_start_hour = config_light_percent["day_start_hour"]
    day_threshold = config_light_percent["day_threshold"]
    night_start_hour = config_light_percent["night_start_hour"]
    night_threshold = config_light_percent["night_threshold"]

    data = fetch(
        datetime_start=datetime_start,
        datetime_end=datetime_end,
        brands=["uhoo"],
        fields=["light"],
    )

    if len(data) == 0:
        return df

    df_minute = pd.DataFrame(data)
    df_minute["time"] = df_minute["time"].dt.floor("h")
    df_minute["hour"] = df_minute["time"].dt.hour
    df_minute["is_day"] = df_minute["hour"].apply(lambda h: day_start_hour <= h < night_start_hour)
    df_minute["threshold"] = df_minute["is_day"].apply(lambda is_day: day_threshold if is_day else night_threshold)
    df_minute["above_threshold"] = df_minute["value"] > df_minute["threshold"]

    df_light_percent = (
        df_minute.groupby(["time", "device", "is_day"])
        .agg(value=("above_threshold", lambda x: (x.sum() / len(x)) * 100))
        .reset_index()
    )
    df_light_percent.rename(columns={"hour": "time"}, inplace=True)
    df_light_percent["brand"] = "uhoo"
    df_light_percent["field"] = df_light_percent["is_day"].apply(
        lambda is_day: "light_percent_day" if is_day else "light_percent_night"
    )
    df_light_percent = df_light_percent[DATAFRAME_COLUMNS]

    df = pd.concat([df, df_light_percent], ignore_index=True)

    return df


def compute_sla(df: pd.DataFrame) -> pd.DataFrame:
    day_start_hour = config.atlas_index["sla"]["day_start_hour"]
    night_start_hour = config.atlas_index["sla"]["night_start_hour"]
    hour = df["time"].dt.hour
    is_day = (hour >= day_start_hour) & (hour < night_start_hour)
    is_sla = df["field"] == "sla"

    df.loc[is_day & is_sla, "field"] = "sla_day"
    df.loc[~is_day & is_sla, "field"] = "sla_night"

    return df
