from __future__ import annotations

from dataclasses import dataclass

from mixonaut.process_matching.models.models import TrackMatch
from mixonaut.process_matching.process.genre_vector import GenreVector


@dataclass(frozen=True, slots=True)
class MatchContext:
    track_id: int
    ref_bpm: float
    ref_key: str
    ref_duration: float
    ref_beat_intensity: float
    ref_mood_emb1: float
    ref_mood_emb2: float

    # Ancien système temporaire
    ref_genre_emb1: float
    ref_genre_emb2: float

    # Nouveau système
    ref_genre_vector: GenreVector

    target_bpm: float
    effective_ref_key: str


@dataclass(frozen=True, slots=True)
class MatchResponse:
    context: MatchContext
    matches: list[TrackMatch]


@dataclass(frozen=True, slots=True)
class MatchFilters:
    id_base: int
    target_bpm: float | None = None
    weights_type: str = "standard"
    max_results: int = 50
    genre: str = "all"
    include_live: bool = False
    artist: str | None = None
    label: str | None = None
    year_min: int | None = None
    year_max: int | None = None
    grouped: bool = True


@dataclass(frozen=True, slots=True)
class GenreBpmRange:
    name: str
    min_bpm: float
    max_bpm: float


GENRE_BPM_RANGES: dict[str, GenreBpmRange] = {
    "all": GenreBpmRange("all", 1, 999),
    "ambient": GenreBpmRange("ambient", 60, 110),
    "large_house": GenreBpmRange("large_house", 105, 135),
    "lo-fi_house": GenreBpmRange("lo-fi_house", 110, 120),
    "afro_house": GenreBpmRange("afro_house", 115, 125),
    "dub_house": GenreBpmRange("dub_house", 115, 125),
    "deep_house": GenreBpmRange("deep_house", 118, 125),
    "melodic_house": GenreBpmRange("melodic_house", 120, 128),
    "house": GenreBpmRange("house", 120, 130),
    "minimal_techno": GenreBpmRange("minimal_techno", 120, 130),
    "tech_house": GenreBpmRange("tech_house", 122, 130),
    "electro": GenreBpmRange("electro", 125, 135),
    "techno": GenreBpmRange("techno", 125, 150),
    "peak_time_techno": GenreBpmRange("peak_time_techno", 130, 140),
    "progressive_house": GenreBpmRange("progressive_house", 126, 132),
    "trance": GenreBpmRange("trance", 128, 145),
    "psy_trance": GenreBpmRange("psy_trance", 138, 148),
    "breakbeat": GenreBpmRange("breakbeat", 125, 140),
    "uk_garage": GenreBpmRange("uk_garage", 130, 140),
    "garage": GenreBpmRange("garage", 130, 135),
    "dubstep": GenreBpmRange("dubstep", 138, 142),
    "hard_techno": GenreBpmRange("hard_techno", 140, 155),
    "hardstyle": GenreBpmRange("hardstyle", 150, 160),
    "footwork": GenreBpmRange("footwork", 155, 165),
    "jungle": GenreBpmRange("jungle", 155, 180),
    "drum&Bass": GenreBpmRange("drum&Bass", 160, 180),
}
