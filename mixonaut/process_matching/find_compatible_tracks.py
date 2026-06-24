"""
2020-08-20 modules hub pour le matching.
"""

from mixonaut.db.matching.matching_queries import (
    get_candidate_tracks,
    get_track_features,
)
from mixonaut.process_matching.models.matching import MatchContext
from mixonaut.process_matching.models.models import TrackMatch
from mixonaut.process_matching.process.key_process import get_effective_ref_key
from mixonaut.process_matching.process.scoring import get_compatible_candidates
from mixonaut.utils.logger import LoggerProtocol, ensure_logger
from mixonaut.process_matching.process.genre_vector import GenreVector
from mixonaut.process_matching.models.matching import MatchFilters


def resolve_target_bpm(
    *,
    ref_bpm: float,
    target_bpm: float | None,
    interactive: bool = True,
) -> float:
    """
    Resolve the effective target BPM.

    If target_bpm is None and interactive=True, ask the user.
    """
    if target_bpm is not None:
        return float(target_bpm)

    if not interactive:
        return float(ref_bpm)

    while True:
        try:
            raw = input(f"Target BPM? [default: {ref_bpm:.1f}] > ").strip()

            if not raw:
                return float(ref_bpm)

            value = float(raw)
            if value <= 0:
                raise ValueError

            return value

        except ValueError:
            print("Please enter a valid BPM (positive number).")


def build_match_context(
    track_id: int,
    *,
    target_bpm: float | None,
    interactive: bool = False,
    logger: LoggerProtocol | None = None,
) -> MatchContext:
    logger = ensure_logger(logger, __name__)

    ref = get_track_features(track_id, logger=logger)
    if not ref:
        raise ValueError(f"Track ID {track_id} introuvable dans audio_features")

    try:
        ref_bpm = float(ref["bpm"])
        ref_key = str(ref["key"])
        ref_duration = float(ref["duration"])

        ref_beat_intensity = float(ref["beat_intensity"])
        ref_mood_emb1 = float(ref["mood_emb1"])
        ref_mood_emb2 = float(ref["mood_emb2"])
        ref_genre_emb1 = float(ref["genre_emb1"])
        ref_genre_emb2 = float(ref["genre_emb2"])
        ref_genre_vector: GenreVector = ref["genre_vector"]
    except KeyError as exc:
        raise KeyError(
            f"Missing required audio feature {exc!s} for track {track_id}"
        ) from exc

    # 🎧 Résolution BPM DJ-aware
    if target_bpm is None:
        if interactive:
            target_bpm = resolve_target_bpm(
                ref_bpm=ref_bpm,
                target_bpm=None,
                interactive=True,
            )
        else:
            target_bpm = ref_bpm

    logger.info("Target BPM resolved: %.2f", target_bpm)

    effective_ref_key = get_effective_ref_key(
        track_id=track_id,
        ref_bpm=ref_bpm,
        ref_key=ref_key,
        target_bpm=target_bpm,
        logger=logger,
    )

    logger.debug(
        "MatchContext built | track_id=%s | ref_bpm=%.2f | target_bpm=%.2f | key=%s → %s",
        track_id,
        ref_bpm,
        target_bpm,
        ref_key,
        effective_ref_key,
    )

    return MatchContext(
        track_id=track_id,
        ref_bpm=ref_bpm,
        ref_key=ref_key,
        ref_duration=ref_duration,
        ref_beat_intensity=ref_beat_intensity,
        ref_mood_emb1=ref_mood_emb1,
        ref_mood_emb2=ref_mood_emb2,
        ref_genre_emb1=ref_genre_emb1,
        ref_genre_emb2=ref_genre_emb2,
        ref_genre_vector=ref_genre_vector,
        target_bpm=target_bpm,
        effective_ref_key=effective_ref_key,
    )


def find_compatible_tracks(
    context: MatchContext,
    filters: MatchFilters,
    logger: LoggerProtocol | None = None,
) -> list[TrackMatch]:
    """
    Find compatible tracks using a pre-resolved MatchContext.

    This function is deterministic:
    - no DB access for reference track
    - no user interaction
    - no grouping logic
    """
    logger = ensure_logger(logger, __name__)

    try:
        logger.debug(
            "Finding compatible tracks | track_id=%s | ref_bpm=%.2f | target_bpm=%.2f | key=%s",
            context.track_id,
            context.ref_bpm,
            context.target_bpm,
            context.effective_ref_key,
        )

        candidates = get_candidate_tracks(
            filters=filters,
            logger=logger,
        )

        if not candidates:
            logger.info("No candidate tracks found")
            return []

        compatibles: list[TrackMatch] = get_compatible_candidates(
            candidates=candidates,
            ref_bpm=context.ref_bpm,
            ref_duration=context.ref_duration,
            ref_beat_intensity=context.ref_beat_intensity,
            ref_mood_emb1=context.ref_mood_emb1,
            ref_mood_emb2=context.ref_mood_emb2,
            ref_genre_vector=context.ref_genre_vector,
            effective_ref_key=context.effective_ref_key,
            target_bpm=context.target_bpm,
            weights_type=filters.weights_type,
            logger=logger,
        )

        if not compatibles:
            logger.info("No compatible tracks found")
            return []

        # nb_results = filters.max_results if filters.grouped else filters.max_results * 6

        # 🔹 tri + limitation ICI (et pas ailleurs)
        compatibles_sorted = sorted(
            compatibles,
            key=lambda m: m["score"],
            reverse=True,
        )  # [:nb_results]

        logger.debug(
            "Returning %d compatible tracks",
            len(compatibles_sorted),
        )

        return compatibles_sorted

    except Exception as exc:  # pylint: disable=broad-except
        logger.exception(
            "Error in find_compatible_tracks (track_id=%s): %s",
            context.track_id,
            exc,
        )
        return []
