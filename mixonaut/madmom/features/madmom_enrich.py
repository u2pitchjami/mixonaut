"""
2025-08-20.

module hub de traitement des features.
"""

from typing import Any
from pathlib import Path
from mixonaut.madmom.features.madmom_calculate import (
    compute_rhythm_stability,
    compute_rhythm_intensity,
    compute_density,
    get_duration_with_ffprobe,
)
from mixonaut.utils.logger import LoggerProtocol, ensure_logger
from mixonaut.utils.config import MADMOM_ANALYSIS_VERSION


def get_best_duration(
    essentia_duration: float | None,
    audio_path: Path,
) -> float | None:
    if essentia_duration is not None and essentia_duration > 0:
        return essentia_duration

    return get_duration_with_ffprobe(audio_path)


def enrich_features_madmom(
    track_features: dict[str, Any],
    duration: float | None,
    logger: LoggerProtocol | None = None,
) -> dict[str, Any]:
    """
    Enriches the features of a track by calculating various metrics such as beat intensity,
    mood, genre, and key.
    Args:
        track_features (dict): The dictionary containing the features of the track.
        duration (float | None): The duration of the track.
        logger (LoggerProtocol | None, optional): The logger instance to use. Defaults to None.

    Returns:
        dict: The enriched track features.
    """
    logger = ensure_logger(logger, __name__)
    try:
        beats_per_second = compute_density(
            track_features.get("beats_count"),
            duration,
        )
        onsets_per_second = compute_density(
            track_features.get("onsets_count"),
            duration,
        )
        downbeats_per_second = compute_density(
            track_features.get("downbeats_count"),
            duration,
        )

        track_features["beats_per_second"] = beats_per_second
        track_features["onsets_per_second"] = onsets_per_second
        track_features["downbeats_per_second"] = downbeats_per_second

        track_features["rhythm_stability"] = compute_rhythm_stability(
            track_features.get("beat_interval_std")
        )

        track_features["rhythm_intensity"] = compute_rhythm_intensity(
            beat_activation_mean=track_features.get("beat_activation_mean"),
            beat_activation_max=track_features.get("beat_activation_max"),
            onsets_per_second=onsets_per_second,
            beats_per_second=beats_per_second,
        )

        track_features["analysis_version"] = MADMOM_ANALYSIS_VERSION
        return track_features
    except Exception as e:
        logger.error(f"Erreur enrichissement features : {e}")
        return track_features
