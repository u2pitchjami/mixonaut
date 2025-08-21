"""
2020-08-20 modules hub pour le matching.
"""

from mixonaut.db.matching.matching_queries import (
    get_candidate_tracks,
    get_track_features,
)
from mixonaut.process_matching.export.export_markdown import (
    group_matches_by_transition_type,
)
from mixonaut.process_matching.process.key_process import get_effective_ref_key
from mixonaut.process_matching.process.scoring import get_compatible_candidates
from mixonaut.utils.logger import LoggerProtocol, ensure_logger, with_child_logger


@with_child_logger
def find_compatible_tracks(
    track_id: int,
    target_bpm: float | None = None,
    max_results: int = 10,
    grouped: bool = False,
    weights_type: str = "standard",
    logger: LoggerProtocol | None = None,
) -> list[dict] | dict[str, list[dict]]:
    """
    Find compatible tracks based on the given track ID.
    Args:
        track_id (int): The ID of the track to find compatible tracks for.
        target_bpm (float, optional): The target BPM to match. Defaults to None.
        max_results (int, optional): The maximum number of results to return. Defaults to 10.
        grouped (bool, optional): Whether to group matches by transition type. Defaults to False.
        weights_type (str, optional): The type of weights to use for matching. Defaults to "standard".
        logger (LoggerProtocol | None, optional): The logger to use for logging. Defaults to None.

    Returns:
        list[dict] | dict[str, list[dict]]: A list of compatible tracks or
        a dictionary with track IDs as keys and lists of dictionaries as values.
    """
    logger = ensure_logger(logger, __name__)
    try:
        ref = get_track_features(track_id, logger=logger)
        if not ref:
            logger.warning(f"Track ID {track_id} introuvable dans audio_features")
            return []

        (
            ref_bpm,
            ref_key,
            ref_beat_intensity,
            ref_mood_emb1,
            ref_mood_emb2,
            ref_genre_emb1,
            ref_genre_emb2,
            ref_duration,
        ) = ref
        effective_ref_key = ref_key

        target_bpm = target_bpm or ref_bpm
        effective_ref_key = get_effective_ref_key(
            track_id, ref_bpm, ref_key, target_bpm, logger=logger
        )

        candidates = get_candidate_tracks(track_id, logger=logger)
        compatibles = get_compatible_candidates(
            candidates,
            ref_bpm,
            ref_duration,
            ref_beat_intensity,
            ref_mood_emb1,
            ref_mood_emb2,
            ref_genre_emb1,
            ref_genre_emb2,
            effective_ref_key,
            target_bpm,
            weights_type,
            logger=logger,
        )

        if not grouped:
            return sorted(compatibles, key=lambda x: x["score"], reverse=True)[
                :max_results
            ]
        else:
            return group_matches_by_transition_type(
                compatibles, effective_ref_key, max_results, logger=logger
            )

    except Exception as e:
        logger.exception(f"Erreur dans find_compatible_tracks: {e}")
        return []
