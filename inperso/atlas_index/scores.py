import pandas as pd

from inperso import config
from inperso.tags import dcs, unit_numbers

AIRTHINGS_PARAM_LIST = ["co2", "humidity", "pm25", "pm10", "sla_day", "sla_night", "temperature"]
UHOO_PARAM_LIST = [
    "ch2o",
    "co",
    "no2",
    "o3",
    "so2",
    "co2",
    "pm10",
    "pm25",
    "temperature",
    "humidity",
    "light_percent_day",
    "light_percent_night",
]


def compute_scores(df: pd.DataFrame) -> pd.DataFrame:
    """Compute the scores for each measurements and put the results in the database."""

    df["unit_number"] = df["device"].map(unit_numbers)

    df = compute_temperatures(df)
    df = compute_scores_per_measurement(df)

    return df


def compute_temperatures(df: pd.DataFrame) -> pd.DataFrame:
    df["date"] = df["time"].dt.date
    df["hour"] = df["time"].dt.hour

    airly_hourly = df[df["brand"] == "airly"]
    airthings_hourly = df[df["brand"] == "airthings"]
    uhoo_hourly = df[df["brand"] == "uhoo"]

    outdoor_lagged = compute_outdoor_temperature(airly_hourly)
    airthings_hourly = compute_temperature(airthings_hourly, outdoor_lagged)
    uhoo_hourly = compute_temperature(uhoo_hourly, outdoor_lagged)

    df = pd.concat([airthings_hourly, uhoo_hourly], ignore_index=True)
    df = df[df["field"] != "temperature"]
    df = df.drop(columns=["date", "hour", "t_rm"], errors="ignore")

    return df


def compute_outdoor_temperature(airly_hourly: pd.DataFrame) -> pd.DataFrame:
    airly_hourly = airly_hourly[airly_hourly["field"] == "temperature"]
    outdoor_daily_avg = airly_hourly.groupby("date")["value"].mean().rename("temperature_outdoor")

    outdoor_lagged = pd.DataFrame({"date": outdoor_daily_avg.index})
    outdoor_lagged["outdoor_avg_prev1"] = outdoor_daily_avg.shift(1).values
    outdoor_lagged["outdoor_avg_prev2"] = outdoor_daily_avg.shift(2).values
    outdoor_lagged["outdoor_avg_prev3"] = outdoor_daily_avg.shift(3).values

    alpha = config.atlas_index["temperature"]["alpha_lagged_outdoor"]
    outdoor_lagged["t_rm"] = (1 - alpha) * (
        outdoor_lagged["outdoor_avg_prev1"]
        + alpha * outdoor_lagged["outdoor_avg_prev2"]
        + alpha**2 * outdoor_lagged["outdoor_avg_prev3"]
    )

    return outdoor_lagged


def compute_temperature(df_hourly: pd.DataFrame, outdoor_lagged: pd.DataFrame) -> pd.DataFrame:
    df_hourly = df_hourly[df_hourly["field"].isin(AIRTHINGS_PARAM_LIST)]
    df_hourly["month"] = df_hourly["time"].dt.month
    df_hourly["dc"] = df_hourly["device"].map(dcs)

    df_hourly = compute_temperature_heating(df_hourly)
    df_hourly = compute_temperature_cooling_mec(df_hourly)
    df_hourly = compute_temperature_cooling_nat(df_hourly, outdoor_lagged)

    df_hourly = df_hourly.drop(columns=["month", "dc"])
    return df_hourly


def compute_temperature_heating(df_hourly: pd.DataFrame) -> pd.DataFrame:
    month_heating_start = config.atlas_index["temperature"]["month_heating_start"]
    month_heating_end = config.atlas_index["temperature"]["month_heating_end"]

    for dc in month_heating_start.keys():
        is_heating = (
            (df_hourly["field"] == "temperature")
            & (df_hourly["dc"] == dc)
            & ((df_hourly["month"] >= month_heating_start[dc]) | (df_hourly["month"] <= month_heating_end[dc]))
        )
        df_hourly.loc[is_heating, "field"] = "temperature_heating"

    return df_hourly


def compute_temperature_cooling_mec(df_hourly: pd.DataFrame) -> pd.DataFrame:
    cooling_is_nat = config.atlas_index["temperature"]["cooling_is_nat"]

    for dc in cooling_is_nat.keys():
        is_cooling = (df_hourly["field"] == "temperature") & (df_hourly["dc"] == dc)
        df_hourly.loc[is_cooling, "field"] = (
            "temperature_cooling_nat" if cooling_is_nat[dc] else "temperature_cooling_mec"
        )

    return df_hourly


def compute_temperature_cooling_nat(df_hourly: pd.DataFrame, outdoor_lagged: pd.DataFrame) -> pd.DataFrame:
    df_hourly["date"] = pd.to_datetime(df_hourly["date"]).dt.date
    df_hourly = df_hourly.merge(outdoor_lagged[["date", "t_rm"]], on="date", how="left")
    df_hourly = df_hourly.drop(
        df_hourly[(df_hourly["field"] == "temperature_cooling_nat") & (df_hourly["t_rm"].isna())].index
    )
    is_temp_cooling_nat = df_hourly["field"] == "temperature_cooling_nat"
    df_hourly.loc[is_temp_cooling_nat, "value"] = (
        df_hourly.loc[is_temp_cooling_nat, "value"]
        + config.atlas_index["temperature"]["cooling_nat_outdoor_factor"] * df_hourly.loc[is_temp_cooling_nat, "t_rm"]
    )

    return df_hourly


def compute_scores_per_measurement(df: pd.DataFrame) -> pd.DataFrame:
    thresholds = config.atlas_index["thresholds"]
    score_functions = {}

    for field, params in thresholds.items():
        function_type = params["type"]
        build_fn = function_type_map[function_type]
        score_functions[field] = build_fn(**params)

    df["score"] = df.apply(
        lambda row: score_functions[row["field"]](row["value"]),
        axis=1,
    )

    return df


def build_fn_smaller(**kwargs):
    high_score = kwargs["high_score"]
    mid_score = kwargs["mid_score"]
    low_score = kwargs["low_score"]

    def scale_to_100_smaller(value):
        if value <= high_score:
            return 100
        elif value == mid_score:
            return 50
        elif value >= low_score:
            return 0
        elif value < mid_score:
            # Linear from 100 to 50 between low and mid
            return 100 - ((value - high_score) / (mid_score - high_score)) * 50
        else:
            # Linear from 50 to 0 between mid and high
            return 50 - ((value - mid_score) / (low_score - mid_score)) * 50

    return scale_to_100_smaller


def build_fn_greater(**kwargs):
    high_score = kwargs["high_score"]
    mid_score = kwargs["mid_score"]
    low_score = kwargs["low_score"]

    def scale_to_100_greater(value):
        if value >= high_score:
            return 100
        elif value == mid_score:
            return 50
        elif value <= low_score:
            return 0
        elif value > mid_score:
            return 50 + ((value - mid_score) / (high_score - mid_score)) * 50
        else:
            return ((value - low_score) / (mid_score - low_score)) * 50

    return scale_to_100_greater


def build_fn_range(**kwargs):
    high_score_lower = kwargs["high_score_lower"]
    high_score_upper = kwargs["high_score_upper"]
    mid_score_lower = kwargs["mid_score_lower"]
    mid_score_upper = kwargs["mid_score_upper"]
    low_score_lower = kwargs["low_score_lower"]
    low_score_upper = kwargs["low_score_upper"]

    def scale_to_100_range(value):
        if high_score_lower <= value <= high_score_upper:
            return 100  # optimal
        elif mid_score_lower <= value < high_score_lower:
            # increase from mid to high
            return 50 + (value - mid_score_lower) / (high_score_lower - mid_score_lower) * 50
        elif mid_score_upper >= value > high_score_upper:
            # decrease from high to mid (if value is slightly above high)
            return 100 - (value - high_score_upper) / (mid_score_upper - high_score_upper) * 50
        elif low_score_lower <= value < mid_score_lower:
            # increase from low to mid
            return (value - low_score_lower) / (mid_score_lower - low_score_lower) * 50
        elif low_score_upper >= value > mid_score_upper:
            # decrease from mid to low (if value is slightly above mid)
            return 50 - (value - mid_score_upper) / (low_score_upper - mid_score_upper) * 50
        else:
            return 0  # far from optimal

    return scale_to_100_range


function_type_map = {"smaller": build_fn_smaller, "greater": build_fn_greater, "range": build_fn_range}
