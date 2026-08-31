from dataclasses import dataclass
from typing import Literal


@dataclass
class ScoreContext:
    building_type: Literal["residential", "school"]
    cooling_type: Literal["natural", "mechanical"]
    heating_season: Literal["heating", "non-heating", "mixed"]
    heating_season_start: str | None = None
    heating_season_end: str | None = None


default_score_context = ScoreContext(
    building_type="residential",
    cooling_type="natural",
    heating_season="mixed",
    heating_season_start=None,
    heating_season_end=None,
)
