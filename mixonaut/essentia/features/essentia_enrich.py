"""
2025-08-20.

module hub de traitement des features.
"""

from mixonaut.essentia.features.essentia_calculate import calculate_beat_intensity
from mixonaut.essentia.features.essentia_genre import get_dominant_genre
from mixonaut.essentia.features.essentia_key import (
    convert_to_camelot,
    get_best_key_from_essentia,
)
from mixonaut.essentia.features.essentia_mood import (
    compute_mood_vector,
    get_dominant_mood,
)
from mixonaut.utils.logger import LoggerProtocol, ensure_logger, with_child_logger
from mixonaut.utils.utils_div import sanitize_value


@with_child_logger
def enrich_features(track_features, logger: LoggerProtocol | None = None):
    """
    Enriches the features of a track by calculating various metrics such as beat intensity,
    mood, genre, and key.
    Args:
        track_features (dict): The dictionary containing the features of the track.
        logger (LoggerProtocol | None, optional): The logger instance to use. Defaults to None.

    Returns:
        dict: The enriched track features.
    """
    logger = ensure_logger(logger, __name__)
    try:
        track_features["bpm"] = sanitize_value(
            track_features.get("bpm"), "bpm", logger=logger
        )
        track_features["rg_track_gain"] = sanitize_value(
            track_features.get("rg_track_gain"), "rg_gain", logger=logger
        )

        track_features["beat_intensity"] = calculate_beat_intensity(
            track_features, logger=logger
        )
        logger.debug(f"beat_intensity : {track_features['beat_intensity']}")

        # track_features["energy_level"] = compute_energy_level(track_features, logger=logger)
        # logger.debug(f"energy_level : {track_features['energy_level']}")

        mood_vector = compute_mood_vector(track_features, logger=logger)
        logger.debug(f"mood_vector : {mood_vector}")

        track_features["mood"] = get_dominant_mood(mood_vector)
        logger.debug(f"mood : {track_features['mood']}")

        track_features["genre"] = get_dominant_genre(track_features)
        logger.debug(f"get_dominant_genre : {track_features['genre']}")

        best_key_data = get_best_key_from_essentia(track_features)
        if best_key_data:
            camelot = convert_to_camelot(best_key_data["key"], best_key_data["scale"])
            track_features["initial_key"] = sanitize_value(
                camelot, "key", logger=logger
            )
            logger.debug(f"initial_key : {track_features['initial_key']}")

        return track_features
    except Exception as e:
        logger.error(f"Erreur enrichissement features : {e}")
        return track_features
