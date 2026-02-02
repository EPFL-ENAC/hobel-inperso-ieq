import pandas as pd

from inperso.fetch import fetch
from inperso.tags import unit_numbers


def preprocess_measurements(datetime_start, datetime_end) -> pd.DataFrame:
    """Retrieve and preprocess the measurements from the database."""

    data = fetch(
        datetime_start=datetime_start,
        datetime_end=datetime_end,
        frequency="1h",
        window_size="1h",
    )

    df = pd.DataFrame(data)
    # Map device to unit_number using the unit_numbers dictionary
    df["unit_number"] = df["device"].map(unit_numbers)

    return df
