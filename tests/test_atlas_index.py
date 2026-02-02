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
