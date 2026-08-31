import logging

import pandas as pd

from inperso import config
from inperso.atlas_index.models import ScoreContext, default_score_context
from inperso.database.write import write
from inperso.tags import dcs, unit_numbers

FALLBACK_OUT_OF_RANGE = (
    "Outdoor running-mean temperature was outside the EN 16798-1 applicability range "
    "(10-30 C) for some rows. Fixed non-adaptive criteria were used as a fallback."
)

FALLBACK_NO_OUTDOOR = (
    "* Outdoor-temperature data were unavailable. The temperature score was calculated "
    "using fixed mechanical-cooling criteria as a fallback and should not be interpreted "
    "as an (EN 16798-1) adaptive-comfort assessment."
)


def compute_scores(
    df: pd.DataFrame,
    context: ScoreContext,
    keep_values: bool = False,
) -> tuple[pd.DataFrame, str | None]:
    """Compute scores where the temperature variant is chosen by an explicit context.

    Returns the scored DataFrame and a fallback note
    that explains any fallback the context path had to apply.
    """
    df["time"] = pd.to_datetime(df["time"])
    df["unit_number"] = df["device"].map(unit_numbers).fillna("unknown")

    df, fallback_note = apply_temperature_context(df, context)
    df = _compute_scores(df, context, write_to_db=False, keep_values=keep_values)
    return df, fallback_note


def compute_scores_inperso(df: pd.DataFrame, write_to_db: bool = False, keep_values: bool = False) -> pd.DataFrame:
    """Compute the scores for each measurements of the inperso influx database and put the results in the database."""

    df["unit_number"] = df["device"].map(unit_numbers).fillna("unknown")

    df = compute_temperatures(df)
    df = _compute_scores(df, default_score_context, write_to_db=write_to_db, keep_values=keep_values)
    return df


def _compute_scores(
    df: pd.DataFrame, context: ScoreContext, write_to_db: bool = False, keep_values: bool = False
) -> pd.DataFrame:
    df = compute_scores_per_measurement(df, context)

    columns = ["time", "field", "unit_number"]
    if keep_values:
        columns.append("value")
    df = df.groupby(columns)["score"].mean().reset_index()

    if write_to_db:
        write_scores(df)

    return df


def compute_temperatures(df: pd.DataFrame) -> pd.DataFrame:
    df["time"] = pd.to_datetime(df["time"])
    df["date"] = df["time"].dt.date
    df["hour"] = df["time"].dt.hour

    airly_hourly = df[df["brand"] == "airly"]
    airthings_hourly = df[df["brand"] == "airthings"]
    uhoo_hourly = df[df["brand"] == "uhoo"]

    outdoor_lagged = compute_outdoor_temperature(airly_hourly)
    airthings_hourly = compute_temperature(airthings_hourly, outdoor_lagged, "airthings")
    uhoo_hourly = compute_temperature(uhoo_hourly, outdoor_lagged, "uhoo")

    df = pd.concat([airthings_hourly, uhoo_hourly], ignore_index=True)
    df = df[df["field"] != "temperature"]
    df = df.drop(columns=["date", "hour", "t_rm"], errors="ignore")

    return df


def _lagged_outdoor_running_mean(daily_avg: pd.Series) -> pd.Series:
    """3-day-lagged running mean of a daily outdoor-temperature series, indexed by date."""
    alpha = config.atlas_index["temperature"]["alpha_lagged_outdoor"]
    prev1 = daily_avg.shift(1)
    prev2 = daily_avg.shift(2)
    prev3 = daily_avg.shift(3)
    return (1 - alpha) * (prev1 + alpha * prev2 + alpha**2 * prev3)


def compute_outdoor_temperature(airly_hourly: pd.DataFrame) -> pd.DataFrame:
    airly_hourly = airly_hourly[airly_hourly["field"] == "temperature"]
    outdoor_daily_avg = airly_hourly.groupby("date")["value"].mean()

    outdoor_lagged = pd.DataFrame({"date": outdoor_daily_avg.index})
    outdoor_lagged["t_rm"] = _lagged_outdoor_running_mean(outdoor_daily_avg).values

    return outdoor_lagged


def compute_temperature(df_hourly: pd.DataFrame, outdoor_lagged: pd.DataFrame, brand: str) -> pd.DataFrame:
    df_hourly = df_hourly[df_hourly["field"].isin(config.atlas_index["fields"][brand])]
    df_hourly["month"] = df_hourly["time"].dt.month
    df_hourly["dc"] = df_hourly["device"].map(dcs).fillna("unknown")

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


def _apply_natural_cooling_correction(df_hourly: pd.DataFrame, rows: pd.Index) -> pd.DataFrame:
    """Add the lagged outdoor-temperature correction to natural-cooling rows."""
    factor = config.atlas_index["temperature"]["cooling_nat_outdoor_factor"]
    df_hourly.loc[rows, "value"] = df_hourly.loc[rows, "value"] + factor * df_hourly.loc[rows, "t_rm"]
    df_hourly.loc[rows, "field"] = "temperature_cooling_nat"
    return df_hourly


def compute_temperature_cooling_nat(df_hourly: pd.DataFrame, outdoor_lagged: pd.DataFrame) -> pd.DataFrame:
    df_hourly["date"] = pd.to_datetime(df_hourly["date"]).dt.date

    if outdoor_lagged.empty:
        logging.warning("Outdoor temperature data is missing. Skipping cooling natural temperature adjustment.")
        df_hourly["t_rm"] = 0.0
    else:
        df_hourly = df_hourly.merge(outdoor_lagged[["date", "t_rm"]], on="date", how="left")

    df_hourly = df_hourly.drop(
        df_hourly[(df_hourly["field"] == "temperature_cooling_nat") & (df_hourly["t_rm"].isna())].index
    )
    is_temp_cooling_nat = df_hourly["field"] == "temperature_cooling_nat"
    nat_rows = df_hourly.index[is_temp_cooling_nat.values]
    return _apply_natural_cooling_correction(df_hourly, nat_rows)


def _get_thresholds(context: ScoreContext) -> dict[str, dict[str, float]]:
    """Get the thresholds for the given context.

    Fills in missing categories with values from default context.
    """
    thresholds = config.atlas_index[default_score_context.building_type]["thresholds"]

    for field, params in config.atlas_index[context.building_type]["thresholds"].items():
        thresholds[field].update(params)

    return thresholds


def compute_scores_per_measurement(df: pd.DataFrame, context: ScoreContext) -> pd.DataFrame:
    thresholds = _get_thresholds(context)
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


def write_scores(df: pd.DataFrame):
    """Write the computed scores to the database."""

    queries = []

    for _, row in df.iterrows():
        time = row["time"]
        unit_number = row["unit_number"]

        fields = {}
        fields[row["field"]] = row["score"]

        queries.append(
            {
                "measurement": "score",
                "tags": {
                    "unit_number": str(unit_number),
                    "atlas_index_hash": config.atlas_index_hash,
                },
                "fields": fields,
                "time": time,
            }
        )

    logging.info(f"Writing {len(queries)} entries to the database.")
    write(queries, use_atlas_index_bucket=True)


function_type_map = {"smaller": build_fn_smaller, "greater": build_fn_greater, "range": build_fn_range}


def _parse_mm_dd(value: str | None) -> tuple[int, int] | None:
    if not value:
        return None
    try:
        month_str, day_str = value.split("/")
        return int(month_str), int(day_str)
    except (TypeError, ValueError):
        return None


def _date_in_season(
    month: int,
    day: int,
    start: tuple[int, int],
    end: tuple[int, int],
) -> bool:
    start_month, start_day = start
    end_month, end_day = end

    if (start_month, start_day) <= (end_month, end_day):
        return (start_month, start_day) <= (month, day) <= (end_month, end_day)

    return (month, day) >= (start_month, start_day) or (month, day) <= (end_month, end_day)


def _compute_outdoor_lagged(df: pd.DataFrame) -> pd.DataFrame:
    """Daily 3-day-lagged running-mean outdoor temp, keyed on every needed date.

    The lagged value for a given date is computed from the three preceding calendar
    days (same lag as ``compute_outdoor_temperature``). The result is keyed on all
    dates present in the input so that an indoor row on any date gets a lagged value
    even when there is no outdoor reading on that exact day.
    """
    outdoor = df[df["field"] == "outdoor_temperature"]
    if outdoor.empty:
        return pd.DataFrame(columns=["date", "t_rm"])

    daily_avg = outdoor.groupby(outdoor["time"].dt.date)["value"].mean()
    needed_dates = df["time"].dt.date
    all_dates = sorted(set(daily_avg.index) | set(needed_dates))
    daily_avg = daily_avg.reindex(all_dates)

    return pd.DataFrame({"date": all_dates, "t_rm": _lagged_outdoor_running_mean(daily_avg).values})


def _season_mask(
    df: pd.DataFrame,
    coverage: str,
    start: tuple[int, int] | None,
    end: tuple[int, int] | None,
) -> pd.Series:
    if coverage == "heating":
        return pd.Series(True, index=df.index)
    if coverage == "non-heating":
        return pd.Series(False, index=df.index)
    if start is None or end is None:
        raise ValueError("Heating season start and end are required when coverage is 'mixed'.")
    return df.apply(
        lambda row: _date_in_season(row["month"], row["day"], start, end),
        axis=1,
    )


def _assign_cooling(
    temp_df: pd.DataFrame,
    non_heat: pd.Index,
    outdoor_lagged: pd.DataFrame,
    cooling_type: str,
) -> tuple[pd.DataFrame, str | None]:
    if cooling_type == "mechanical":
        temp_df.loc[non_heat, "field"] = "temperature_cooling_mec"
        return temp_df, None

    if outdoor_lagged.empty:
        temp_df.loc[non_heat, "field"] = "temperature_cooling_mec"
        note = FALLBACK_NO_OUTDOOR if not non_heat.empty else None
        return temp_df, note

    temp_df = temp_df.merge(outdoor_lagged[["date", "t_rm"]], on="date", how="left")
    temp_df["t_rm"] = pd.to_numeric(temp_df["t_rm"], errors="coerce")
    t_rm = temp_df.loc[non_heat, "t_rm"]
    in_range = ((t_rm > 10.0) & (t_rm < 30.0)).fillna(False)
    nat = non_heat[in_range.values]
    fallback = non_heat[~in_range.values]

    temp_df = _apply_natural_cooling_correction(temp_df, nat)
    temp_df.loc[fallback, "field"] = "temperature_cooling_mec"

    note = FALLBACK_OUT_OF_RANGE if not fallback.empty else None
    return temp_df, note


def apply_temperature_context(
    df: pd.DataFrame,
    context: ScoreContext,
) -> tuple[pd.DataFrame, str | None]:
    """Assign the correct temperature score variant based on user-provided context.

    The input DataFrame must contain a ``field`` column. Outdoor temperature rows
    are identified by the field name ``outdoor_temperature`` (e.g. uploaded columns
    such as "outdoor temperature" or "outside temp" are mapped to this name before
    this function is called).

    Raises ``ValueError`` when the context is incomplete or inconsistent.
    """
    coverage = context.heating_season
    start = _parse_mm_dd(context.heating_season_start)
    end = _parse_mm_dd(context.heating_season_end)
    if coverage == "mixed" and (start is None or end is None):
        raise ValueError("Heating season start and end are required when coverage is 'mixed'.")

    outdoor_lagged = _compute_outdoor_lagged(df)

    df["month"] = df["time"].dt.month
    df["day"] = df["time"].dt.day
    df["date"] = df["time"].dt.date

    is_temp = df["field"] == "temperature"
    temp_df = df[is_temp].copy()
    other_df = df[~is_temp].copy()

    fallback_note: str | None = None
    if not temp_df.empty:
        is_heating = _season_mask(df, coverage, start, end).loc[temp_df.index]
        heat = temp_df.index[is_heating.values]
        temp_df.loc[heat, "field"] = "temperature_heating"
        non_heat = temp_df.index[~is_heating.values]
        temp_df, fallback_note = _assign_cooling(temp_df, non_heat, outdoor_lagged, context.cooling_type)

    df = pd.concat([other_df, temp_df], ignore_index=True)
    df = df[df["field"] != "outdoor_temperature"]
    df = df.drop(columns=["month", "day", "date", "t_rm"], errors="ignore")

    return df, fallback_note
