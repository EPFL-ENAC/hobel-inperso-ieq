"""Compute the hourly ATLAS index and populate the database."""

import logging
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

from inperso import config
from inperso.atlas_index.preprocessing import preprocess_measurements
from inperso.atlas_index.scores import compute_scores
from inperso.database.buckets import ensure_bucket_exists
from inperso.database.delete import delete
from inperso.database.read import query
from inperso.database.write import WriteQuery, write


def main():
    """Compute the ATLAS index starting from the latest computed time."""

    datetime_start = get_latest_index_computation_time()

    if datetime_start is None:
        datetime_start = get_earliest_data_time()

    if datetime_start is None:
        datetime_start = config.datetime_start

    datetime_end = datetime.now(timezone.utc)

    # Chunk computation by month
    current_start = datetime_start
    while current_start < datetime_end:
        next_month = (current_start.replace(day=1) + timedelta(days=32)).replace(day=1)
        current_end = min(next_month, datetime_end)
        compute_index(current_start, current_end)
        current_start = current_end


def get_latest_index_computation_time() -> datetime | None:
    """Get the most recent datetime for which the ATLAS index has been computed."""

    bucket_name = config.db["bucket_atlas_index"]
    ensure_bucket_exists(bucket_name)
    clean_outdated_index_data()

    query_str = (
        f'from(bucket:"{bucket_name}") '
        "|> range(start: 0, stop: now()) "
        f'|> filter(fn: (r) => r["_measurement"] == "index") '
        "|> last() "
    )
    result = query(query_str)

    if result is None or len(result) == 0:
        return None

    return max(r.records[0].get_time() for r in result)


def clean_outdated_index_data():
    """Remove score and index data computed using old configuration parameters."""

    delete(
        bucket=config.db["bucket_atlas_index"],
        predicate=f'atlas_index_hash!="{config.atlas_index_hash}"',
    )


def get_earliest_data_time() -> datetime | None:
    """Get the earliest datetime for which data is available in the database."""

    query_str = f'from(bucket:"{config.db["bucket"]}") |> range(start: 0, stop: now()) |> first() '
    result = query(query_str)

    if result is None or len(result) == 0:
        return None

    return min(r.records[0].get_time() for r in result)


def compute_index(datetime_start, datetime_end):
    """Compute the ATLAS index and put the results in the database."""

    # Need 3 days to compute lagged outdoor temperature, and 1 more day for off-by-one issues
    datetime_start = datetime_start - timedelta(days=4)

    logging.info(f"Computing ATLAS index from {datetime_start} to {datetime_end}")
    measurements = preprocess_measurements(datetime_start, datetime_end)
    scores = compute_scores(measurements)
    scores["score"] = np.log(scores["score"])

    fields_per_category = config.atlas_index["index_fields"]
    category_per_field = {field: category for category, fields in fields_per_category.items() for field in fields}
    scores["category"] = scores["field"].map(category_per_field)
    indices = scores.groupby(["time", "unit_number", "category"], as_index=False)["score"].mean()
    indices = indices.pivot(index=["time", "unit_number"], columns="category", values="score").reset_index()

    weights = config.atlas_index["weights"]
    indices["atlas_index"] = indices.apply(
        lambda row: sum(row[category] * weights[category] for category in weights.keys()), axis=1
    )
    for category in list(weights.keys()) + ["atlas_index"]:
        indices[category] = np.exp(indices[category])

    write_indices(indices)

    return indices


def write_indices(df: pd.DataFrame) -> None:
    """Write the computed indices to the database."""

    bucket_name = config.db["bucket_atlas_index"]
    queries = []

    for _, row in df.iterrows():
        time = row["time"]
        unit_number = row["unit_number"]

        fields = {
            category: row[category]
            for category in df.columns
            if category not in ["time", "unit_number"] and not pd.isna(row[category])
        }

        queries.append(
            {
                "measurement": "index",
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


if __name__ == "__main__":
    main()
