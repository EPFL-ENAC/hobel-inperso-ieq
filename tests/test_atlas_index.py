import pandas as pd
import pytest


def test_config_load():
    """Ensure the configuration yaml is correctly loaded."""

    from inperso.config import atlas_index

    assert isinstance(atlas_index, dict)

    assert "unit_conversion_factors" in atlas_index
    assert isinstance(atlas_index["unit_conversion_factors"], dict)

    assert "thresholds" in atlas_index
    for parameter in atlas_index["thresholds"]:
        assert isinstance(atlas_index["thresholds"][parameter], dict)
        threshold_params = atlas_index["thresholds"][parameter]

        assert "type" in threshold_params
        threshold_type = threshold_params["type"]

        if threshold_type == "smaller" or threshold_type == "greater":
            for score_type in ["high_score", "mid_score", "low_score"]:
                assert score_type in threshold_params
                assert isinstance(threshold_params[score_type], (int, float))

            if threshold_type == "smaller":
                assert threshold_params["high_score"] < threshold_params["mid_score"] < threshold_params["low_score"]

            else:  # greater
                assert threshold_params["high_score"] > threshold_params["mid_score"] > threshold_params["low_score"]

        elif threshold_type == "range":
            for score_type in [
                "high_score_lower",
                "high_score_upper",
                "mid_score_lower",
                "mid_score_upper",
                "low_score_lower",
                "low_score_upper",
            ]:
                assert score_type in threshold_params
                assert isinstance(threshold_params[score_type], (int, float))

            assert (
                threshold_params["low_score_lower"]
                < threshold_params["mid_score_lower"]
                < threshold_params["high_score_lower"]
                < threshold_params["high_score_upper"]
                < threshold_params["mid_score_upper"]
                < threshold_params["low_score_upper"]
            )

        else:
            raise ValueError(f"Unknown threshold type: {threshold_type}")


def test_apply_temperature_context_variants():
    """Heating / non-heating bypass month bounds; mixed splits; outdoor column removed."""
    from inperso.atlas_index.scores import apply_temperature_context

    rows = pd.DataFrame(
        [
            ("2026-01-15 12:00:00", "temperature", 20.0),
            ("2026-07-15 12:00:00", "temperature", 26.0),
        ],
        columns=["time", "field", "value"],
    )
    rows["time"] = pd.to_datetime(rows["time"])
    outdoor = pd.DataFrame(
        [
            ("2026-07-12", "outdoor_temperature", 15.0),
            ("2026-07-13", "outdoor_temperature", 16.0),
            ("2026-07-14", "outdoor_temperature", 17.0),
        ],
        columns=["time", "field", "value"],
    )
    outdoor["time"] = pd.to_datetime(outdoor["time"])
    df = pd.concat([rows, outdoor], ignore_index=True)

    out, _ = apply_temperature_context(
        df.copy(), {"cooling_type": "mechanical", "heating_season": "heating"}
    )
    assert set(out["field"]) == {"temperature_heating"}

    out, _ = apply_temperature_context(
        df.copy(), {"cooling_type": "mechanical", "heating_season": "non-heating"}
    )
    assert set(out["field"]) == {"temperature_cooling_mec"}

    out, _ = apply_temperature_context(
        df.copy(),
        {
            "cooling_type": "mechanical",
            "heating_season": "mixed",
            "heating_season_start": "11/01",
            "heating_season_end": "03/31",
        },
    )
    assert {"temperature_heating", "temperature_cooling_mec"} <= set(out["field"])

    # The outdoor-temperature rows are removed from the result.
    assert "outdoor_temperature" not in set(out["field"])


def test_apply_temperature_context_requires_context():
    """apply_temperature_context raises ValueError when the context is incomplete."""
    from inperso.atlas_index.scores import apply_temperature_context

    df = pd.DataFrame(
        [("2026-07-15 12:00:00", "temperature", 26.0)],
        columns=["time", "field", "value"],
    )
    df["time"] = pd.to_datetime(df["time"])

    with pytest.raises(ValueError):
        apply_temperature_context(df.copy(), {"cooling_type": "natural"})

    with pytest.raises(ValueError):
        apply_temperature_context(
            df.copy(),
            {"cooling_type": "natural", "heating_season": "mixed"},
        )


def test_apply_temperature_context_uses_lagged_outdoor():
    """Natural cooling uses the 3-day-lagged outdoor running mean, not same-day value."""
    from inperso import config
    from inperso.atlas_index.scores import apply_temperature_context

    alpha = config.atlas_index["temperature"]["alpha_lagged_outdoor"]
    factor = config.atlas_index["temperature"]["cooling_nat_outdoor_factor"]

    # Outdoor readings for the 3 days before the indoor row (prev3, prev2, prev1).
    outdoor = pd.DataFrame(
        [
            ("2026-01-12", "outdoor_temperature", 10.0),
            ("2026-01-13", "outdoor_temperature", 20.0),
            ("2026-01-14", "outdoor_temperature", 30.0),
        ],
        columns=["time", "field", "value"],
    )
    outdoor["time"] = pd.to_datetime(outdoor["time"])
    rows = pd.DataFrame(
        [("2026-01-15 12:00:00", "temperature", 26.0)],
        columns=["time", "field", "value"],
    )
    rows["time"] = pd.to_datetime(rows["time"])
    df = pd.concat([rows, outdoor], ignore_index=True)

    out, _ = apply_temperature_context(
        df.copy(), {"cooling_type": "natural", "heating_season": "non-heating"}
    )

    # t_rm at 01-15 uses outdoor from 01-14, 01-13, 01-12 (not 01-15).
    t_rm = (1 - alpha) * (30.0 + alpha * 20.0 + alpha**2 * 10.0)
    assert 10.0 < t_rm < 30.0
    assert out["field"].iloc[0] == "temperature_cooling_nat"
    assert out["value"].iloc[0] == pytest.approx(26.0 + factor * t_rm)


def test_compute_scores_with_context():
    """compute_scores_with_context scores the context path and returns a fallback note."""
    from inperso.atlas_index.scores import compute_scores_with_context

    df = pd.DataFrame(
        [
            ("2026-01-15 12:00:00", "temperature", 20.0, ""),
            ("2026-07-15 12:00:00", "temperature", 26.0, ""),
        ],
        columns=["time", "field", "value", "device"],
    )
    df["time"] = pd.to_datetime(df["time"])

    context = {
        "cooling_type": "mechanical",
        "heating_season": "non-heating",
    }
    out, fallback_note = compute_scores_with_context(df.copy(), context, keep_values=True)

    assert "score" in out.columns
    assert set(out["field"]) == {"temperature_cooling_mec"}
    # keep_values keeps the value column through the aggregation.
    assert "value" in out.columns
    # Rows are aggregated per (time, field, unit_number).
    assert "unit_number" in out.columns
    assert fallback_note is None
