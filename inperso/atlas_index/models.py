from typing import Literal, TypedDict


class ScoreContext(TypedDict, total=False):
    building_type: Literal["residential", "school"]
    cooling_type: Literal["natural", "mechanical"]
    heating_season: Literal["heating", "non-heating", "mixed"]
    heating_season_start: str | None
    heating_season_end: str | None
