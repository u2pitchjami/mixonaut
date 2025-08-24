"""
2025-08-21 sql queries for matching.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Mapping

from mixonaut.db.access import select_all, select_one
from mixonaut.process_matching.models.models import (
    CandidateTrack,
    EnrichedTrackMatch,
    TrackFeatures,
    TrackMatch,
)
from mixonaut.utils.logger import LoggerProtocol, ensure_logger, with_child_logger


@with_child_logger
def get_track_features(
    track_id: int, logger: LoggerProtocol | None = None
) -> TrackFeatures | None:
    """
    Retrieves the features of an audio track.

    Args:
        track_id (int): The ID of the audio track to retrieve features for.
        logger (str, optional): The name of the logger. Defaults to None.

    Returns:
        tuple | None: A dictionary containing the audio track's features, or None if no matching track is found.
    """
    logger = ensure_logger(logger, __name__)
    query = """
    SELECT bpm, initial_key, beat_intensity, mood_emb_1, mood_emb_2, genre_emb_1, genre_emb_2, duration
    FROM audio_features
    WHERE id = ?
    """
    raw = select_one(query, (track_id,), logger=logger)
    if raw is None:
        return None
    return {
        "bpm": raw["bpm"],
        "key": raw["key"],
        "beat_intensity": raw["beat_intensity"],
        "mood_emb1": raw["mood_emb1"],
        "mood_emb2": raw["mood_emb2"],
        "genre_emb1": raw["genre_emb1"],
        "genre_emb2": raw["genre_emb2"],
        "duration": raw["duration"],
    }


@with_child_logger
def get_transpositions(
    track_id: int, logger: LoggerProtocol | None = None
) -> sqlite3.Row | None:
    """
    Retrieves the transpositions for a given track.

    Args:
        track_id (int): The ID of the track to retrieve transpositions for.
        logger (str, optional): The logger name. Defaults to None.

    Returns:
        tuple | None: A tuple containing the transposition information or None if no data is found.
    """
    logger = ensure_logger(logger, __name__)
    return select_one(
        "SELECT * FROM track_transpositions WHERE id = ?", (track_id,), logger=logger
    )


@with_child_logger
def get_candidate_tracks(
    track_id: int, logger: LoggerProtocol | None = None
) -> list[CandidateTrack]:
    """
    Récupère les candidats (toutes les pistes sauf `track_id`), sous forme typée.
    """
    logger = ensure_logger(logger, __name__)
    query = """
    SELECT
        id,
        bpm,
        initial_key AS key,
        beat_intensity,
        mood_emb_1 AS mood_emb1,
        mood_emb_2 AS mood_emb2,
        genre_emb_1 AS genre_emb1,
        genre_emb_2 AS genre_emb2,
        duration
    FROM audio_features
    WHERE id != ?
    """
    try:
        rows = select_all(query, (track_id,), logger=logger)  # -> list[dict] idéalement
        # Si select_all renvoie des sqlite3.Row, convertir :
        candidates: list[CandidateTrack] = [
            {
                "id": int(row["id"]),
                "bpm": float(row["bpm"]),
                "key": str(row["key"]),
                "beat_intensity": float(row["beat_intensity"]),
                "mood_emb1": float(row["mood_emb1"]),
                "mood_emb2": float(row["mood_emb2"]),
                "genre_emb1": float(row["genre_emb1"]),
                "genre_emb2": float(row["genre_emb2"]),
                "duration": float(row["duration"]),
            }
            for row in rows
        ]
        return candidates
    except Exception as exc:  # pylint: disable=broad-except
        logger.error("Erreur lors de la récupération des candidats: %s", exc)
        return []


@with_child_logger
def enrich_matches_with_metadata(
    matches: list[TrackMatch],
    logger: LoggerProtocol | None = None,
) -> list[EnrichedTrackMatch]:
    """
    Ajoute artist/album/title à chaque match depuis la table items.

    Retourne une nouvelle liste (ne modifie pas l'entrée).
    """
    logger = ensure_logger(logger, __name__)
    enriched: list[EnrichedTrackMatch] = []

    for match in matches:
        row = select_one(
            "SELECT artist, album, title FROM items WHERE id = ?",
            (match["id"],),
            logger=logger,
        )

        artist: str = "Unknown"
        album: str = "Unknown"
        title: str = "Unknown"

        try:
            if row:
                if isinstance(row, Mapping):
                    # sqlite3.Row ou dict-like
                    artist = str(row.get("artist", "Unknown"))
                    album = str(row.get("album", "Unknown"))
                    title = str(row.get("title", "Unknown"))
                elif isinstance(row, (list, tuple)) and len(row) >= 3:
                    artist = str(row[0])
                    album = str(row[1])
                    title = str(row[2])
                else:
                    logger.warning(
                        "Format de ligne inattendu pour id=%s: %r", match["id"], row
                    )
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("Échec enrichissement metadata id=%s : %s", match["id"], exc)

        enriched.append({**match, "artist": artist, "album": album, "title": title})

    return enriched
