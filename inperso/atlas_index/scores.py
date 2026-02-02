from inperso.tags import unit_numbers


def compute_scores(measurements):
    """Compute the scores for each measurements and put the results in the database."""

    df["unit_number"] = df["device"].map(unit_numbers)
