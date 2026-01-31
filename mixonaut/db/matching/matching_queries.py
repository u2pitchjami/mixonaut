"""
2025-08-21 sql queries for matching.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from mixonaut.db.access import select_all, select_one
from mixonaut.process_matching.models.models import (
    CandidateTrack,
    EnrichedTrackMatch,
    TrackFeatures,
    TrackMatch,
)
from mixonaut.utils.config import BEETS_MUSIC, NAVIDROME_ROOT
from mixonaut.utils.logger import LoggerProtocol, ensure_logger, with_child_logger
from mixonaut.utils.utils_div import ensure_to_path, map_to_navidrome_path


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
        "key": raw["initial_key"],
        "beat_intensity": raw["beat_intensity"],
        "mood_emb1": raw["mood_emb_1"],
        "mood_emb2": raw["mood_emb_2"],
        "genre_emb1": raw["genre_emb_1"],
        "genre_emb2": raw["genre_emb_2"],
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
    WHERE bpm IS NOT NULL
    AND bpm > 0
    AND initial_key IS NOT NULL
    AND beat_intensity IS NOT NULL
    AND duration IS NOT NULL
    AND duration > 0
    AND mood_emb_1 IS NOT NULL
    AND mood_emb_2 IS NOT NULL
    AND genre_emb_1 IS NOT NULL
    AND genre_emb_2 IS NOT NULL;
    """
    try:
        rows = select_all(query, logger=logger)  # -> list[dict] idéalement
        logger.debug("Nombre de candidats récupérés: %d", len(rows))
        logger.debug("Exemple de candidat: %r", rows[0] if rows else "Aucun")
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
    Enrich TrackMatch with artist / album / title / Navidrome-compatible path.

    - Never raises
    - Always returns EnrichedTrackMatch with stable keys
    """
    logger = ensure_logger(logger, __name__)
    enriched: list[EnrichedTrackMatch] = []

    logger.debug(
        "Enriching %d matches with metadata",
        len(matches),
    )

    for match in matches:
        track_id = match["id"]

        artist = "Unknown Artist"
        album = "Unknown Album"
        title = "Unknown Title"
        navidrome_path = "Unknown"

        try:
            row = select_one(
                "SELECT artist, album, title, path FROM items WHERE id = ?",
                (track_id,),
                logger=logger,
            )

            if row is None:
                logger.warning(
                    "No metadata found for track id=%s",
                    track_id,
                )
            else:
                try:
                    row_map = _normalize_db_row(row)
                except TypeError as exc:
                    logger.warning(
                        "Invalid metadata row for track id=%s: %s",
                        track_id,
                        exc,
                    )
                else:
                    artist = str(row_map.get("artist") or artist)
                    album = str(row_map.get("album") or album)
                    title = str(row_map.get("title") or title)

                    source_path = row_map.get("path")
                    logger.debug(
                        "RAW PATH CHECK | id=%s | row_path=%r | type=%s",
                        track_id,
                        row_map.get("path"),
                        type(row_map.get("path")),
                    )
                    raw_path = row_map.get("path")

                    if raw_path:
                        try:
                            source_path = ensure_to_path(raw_path)

                            navidrome_path = map_to_navidrome_path(
                                source_path=str(source_path),
                                source_root=Path(BEETS_MUSIC),
                                navidrome_root=NAVIDROME_ROOT,
                                logger=logger,
                            )

                            logger.debug(
                                "Mapped path for track id=%s: %s",
                                track_id,
                                navidrome_path,
                            )

                        except Exception as exc:  # pylint: disable=broad-except
                            logger.warning(
                                "Path mapping failed for track id=%s (raw=%r): %s",
                                track_id,
                                raw_path,
                                exc,
                            )

        except Exception as exc:  # pylint: disable=broad-except
            logger.exception(
                "Unexpected error while enriching track id=%s: %s",
                track_id,
                exc,
            )

        enriched.append(
            {
                **match,
                "artist": artist,
                "album": album,
                "title": title,
                "path": navidrome_path,
            }
        )

    return enriched


def enrich_matches(
    matches: list[TrackMatch],
    logger: LoggerProtocol | None = None,
) -> list[EnrichedTrackMatch]:
    return enrich_matches_with_metadata(matches, logger=logger)


def _normalize_db_row(row: Any) -> Mapping[str, Any]:
    """
    Normalize sqlite3.Row / SQLAlchemy Row / dict into a Mapping[str, Any].
    """
    if isinstance(row, Mapping):
        return row

    if hasattr(row, "keys"):
        # sqlite3.Row or SQLAlchemy Row
        return {key: row[key] for key in row.keys()}

    raise TypeError(f"Unsupported DB row type: {type(row)!r}")
