import pandas as pd

from inperso.tags import unit_numbers


def compute_scores(df: pd.DataFrame) -> pd.DataFrame:
    """Compute the scores for each measurements and put the results in the database."""

    df["unit_number"] = df["device"].map(unit_numbers)

    return df
