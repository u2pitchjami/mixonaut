from __future__ import annotations

from dataclasses import dataclass

from mixonaut.process_matching.models.models import TrackMatch


@dataclass(frozen=True, slots=True)
class MatchContext:
    track_id: int

    # --- Référence brute ---
    ref_bpm: float
    ref_key: str
    ref_duration: float

    ref_beat_intensity: float
    ref_mood_emb1: float
    ref_mood_emb2: float
    ref_genre_emb1: float
    ref_genre_emb2: float

    # --- Résolution DJ ---
    target_bpm: float
    effective_ref_key: str


@dataclass(frozen=True, slots=True)
class MatchResponse:
    context: MatchContext
    matches: list[TrackMatch]
