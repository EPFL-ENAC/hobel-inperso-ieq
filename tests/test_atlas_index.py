import logging

import pandas as pd
import pytest


def test_config_load():
    """Ensure the configuration yaml is correctly loaded."""

    from inperso.config import atlas_index

    assert isinstance(atlas_index, dict)

    assert "unit_conversion_factors" in atlas_index
    assert isinstance(atlas_index["unit_conversion_factors"], dict)

    assert "thresholds" in atlas_index
    thresholds = atlas_index["thresholds"]
    assert "residential" in thresholds
    assert "school" in thresholds

    for building_type in thresholds:
        assert isinstance(thresholds[building_type], dict)
        for parameter in thresholds[building_type]:
            validate_threshold_params(thresholds[building_type][parameter])


def validate_threshold_params(threshold_params):
    """Check that a field's threshold parameters are consistent."""
    assert isinstance(threshold_params, dict)
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
    from inperso.atlas_index.models import ScoreContext
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
        df.copy(), ScoreContext("residential", "mechanical", "heating")
    )
    assert set(out["field"]) == {"temperature_heating"}

    out, _ = apply_temperature_context(
        df.copy(), ScoreContext("residential", "mechanical", "non-heating")
    )
    assert set(out["field"]) == {"temperature_cooling_mec"}

    out, _ = apply_temperature_context(
        df.copy(),
        ScoreContext("residential", "mechanical", "mixed", "11/01", "03/31"),
    )
    assert {"temperature_heating", "temperature_cooling_mec"} <= set(out["field"])

    # The outdoor-temperature rows are removed from the result.
    assert "outdoor_temperature" not in set(out["field"])


def test_apply_temperature_context_requires_context():
    """apply_temperature_context raises ValueError when the context is incomplete."""
    from inperso.atlas_index.models import ScoreContext
    from inperso.atlas_index.scores import apply_temperature_context

    df = pd.DataFrame(
        [("2026-07-15 12:00:00", "temperature", 26.0)],
        columns=["time", "field", "value"],
    )
    df["time"] = pd.to_datetime(df["time"])

    # Mixed season requires both heating-season bounds.
    with pytest.raises(ValueError):
        apply_temperature_context(
            df.copy(), ScoreContext("residential", "natural", "mixed")
        )

    with pytest.raises(ValueError):
        apply_temperature_context(
            df.copy(),
            ScoreContext("residential", "natural", "mixed", None, "03/31"),
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

    from inperso.atlas_index.models import ScoreContext

    out, _ = apply_temperature_context(
        df.copy(), ScoreContext("residential", "natural", "non-heating")
    )

    # t_rm at 01-15 uses outdoor from 01-14, 01-13, 01-12 (not 01-15).
    t_rm = (1 - alpha) * (30.0 + alpha * 20.0 + alpha**2 * 10.0)
    assert 10.0 < t_rm < 30.0
    assert out["field"].iloc[0] == "temperature_cooling_nat"
    assert out["value"].iloc[0] == pytest.approx(26.0 + factor * t_rm)


def test_compute_scores():
    """compute_scores scores the context path and returns a fallback note."""
    from inperso.atlas_index.models import ScoreContext
    from inperso.atlas_index.scores import compute_scores

    df = pd.DataFrame(
        [
            ("2026-01-15 12:00:00", "temperature", 20.0, ""),
            ("2026-07-15 12:00:00", "temperature", 26.0, ""),
        ],
        columns=["time", "field", "value", "device"],
    )
    df["time"] = pd.to_datetime(df["time"])

    context = ScoreContext("residential", "mechanical", "non-heating")
    out, fallback_note = compute_scores(df.copy(), context, keep_values=True)

    assert "score" in out.columns
    assert set(out["field"]) == {"temperature_cooling_mec"}
    # keep_values keeps the value column through the aggregation.
    assert "value" in out.columns
    # Rows are aggregated per (time, field, unit_number).
    assert "unit_number" in out.columns
    assert fallback_note is None


def test_compute_scores_drops_fields_without_thresholds(caplog):
    """Fields without threshold parameters are dropped, not scored."""
    import logging

    from inperso.atlas_index.models import ScoreContext
    from inperso.atlas_index.scores import compute_scores

    df = pd.DataFrame(
        [
            ("2026-07-15 12:00:00", "temperature", 25.0, ""),
            ("2026-07-15 12:00:00", "unknown_field", 42.0, ""),
        ],
        columns=["time", "field", "value", "device"],
    )
    df["time"] = pd.to_datetime(df["time"])

    with caplog.at_level(logging.WARNING):
        out, _ = compute_scores(
            df.copy(), ScoreContext("residential", "mechanical", "non-heating"), keep_values=True
        )

    # Only fields with thresholds are scored.
    assert set(out["field"]) == {"temperature_cooling_mec"}


def test_light_fields_selected_by_context():
    """School keeps raw light and drops percent rows; residential is the reverse."""
    from inperso.atlas_index.models import ScoreContext
    from inperso.atlas_index.scores import _select_light_fields

    rows = [
        ("2026-07-15 10:00:00", "light", 800.0, ""),
        ("2026-07-15 11:00:00", "light_percent_day", 60.0, ""),
        ("2026-07-15 23:00:00", "light_percent_night", 10.0, ""),
        ("2026-07-15 12:00:00", "co2", 700.0, ""),
    ]
    df = pd.DataFrame(rows, columns=["time", "field", "value", "device"])

    school = _select_light_fields(df.copy(), ScoreContext("school", "natural", "heating"))
    assert set(school["field"]) == {"light", "co2"}

    residential = _select_light_fields(df.copy(), ScoreContext("residential", "natural", "heating"))
    assert set(residential["field"]) == {"light_percent_day", "light_percent_night", "co2"}


def test_school_light_scored_with_lux_thresholds():
    """School raw light rows are scored with the light thresholds (lux)."""
    from inperso.atlas_index.models import ScoreContext
    from inperso.atlas_index.scores import compute_scores

    df = pd.DataFrame(
        [("2026-07-15 10:00:00", "light", 1000.0, "")],
        columns=["time", "field", "value", "device"],
    )
    df["time"] = pd.to_datetime(df["time"])

    out, _ = compute_scores(df.copy(), ScoreContext("school", "natural", "heating"), keep_values=True)

    # 1000 lux is the score-100 boundary for schools.
    assert set(out["field"]) == {"light"}
    assert out["score"].iloc[0] == 100


def test_get_thresholds_does_not_mutate_config():
    """Thresholds for non-default contexts do not leak into the loaded config."""
    from inperso import config
    from inperso.atlas_index.models import ScoreContext
    from inperso.atlas_index.scores import _get_thresholds

    mid_school = config.atlas_index["thresholds"]["school"]["co2"]["mid_score"]
    mid_residential = config.atlas_index["thresholds"]["residential"]["co2"]["mid_score"]

    _get_thresholds(ScoreContext("school", "natural", "heating"))

    assert config.atlas_index["thresholds"]["school"]["co2"]["mid_score"] == mid_school
    assert config.atlas_index["thresholds"]["residential"]["co2"]["mid_score"] == mid_residential


def test_school_score_uses_school_thresholds():
    """School context scores use the school threshold values."""
    from inperso.atlas_index.models import ScoreContext
    from inperso.atlas_index.scores import compute_scores

    df = pd.DataFrame(
        [("2026-07-15 10:00:00", "co2", 1000.0, "")],
        columns=["time", "field", "value", "device"],
    )
    df["time"] = pd.to_datetime(df["time"])

    out, _ = compute_scores(df.copy(), ScoreContext("school", "natural", "heating"), keep_values=True)

    # 1000 ppm is the school score-50 boundary for co2.
    assert out["score"].iloc[0] == 50


def test_weighted_atlas_index_renormalizes():
    """Missing categories are skipped and weights are renormalized."""
    from inperso.atlas_index.index import weighted_atlas_index

    weights = {"iaq": 0.25, "thermal": 0.25, "lux": 0.25, "noise": 0.25}

    row = {"iaq": 4.0, "lux": 2.0, "noise": 2.0}
    result = weighted_atlas_index(row, weights, ["iaq", "lux", "noise"])

    # (4 * 0.25 + 2 * 0.25 + 2 * 0.25) / (0.25 + 0.25 + 0.25) = 8/3
    assert result == pytest.approx(8.0 / 3.0)

    # All categories present: plain weighted mean.
    row_full = {"iaq": 1.0, "thermal": 1.0, "lux": 1.0, "noise": 1.0}
    assert weighted_atlas_index(row_full, weights, ["iaq", "thermal", "lux", "noise"]) == 1.0

    # No categories with data: NaN.
    assert pytest.approx(float("nan")) != weighted_atlas_index({}, weights, [])


def test_index_fields_cover_new_fields():
    """rn, reverberation_time and light are mapped to index categories."""
    from inperso.config import atlas_index

    fields_per_category = atlas_index["index_fields"]

    for field, category in [("rn", "iaq"), ("reverberation_time", "noise"), ("light", "lux")]:
        assert field in fields_per_category[category], f"{field} must be in {category}"
