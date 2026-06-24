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
from mixonaut.process_matching.models.matching import GENRE_BPM_RANGES
from mixonaut.utils.config import BEETS_MUSIC, NAVIDROME_ROOT
from mixonaut.utils.logger import LoggerProtocol, ensure_logger
from mixonaut.utils.utils_div import ensure_to_path, map_to_navidrome_path
from mixonaut.process_matching.process.genre_vector import (
    get_genre_columns_sql,
    build_genre_vector,
)
from typing import cast
from mixonaut.process_matching.models.matching import MatchFilters


def get_track_features(
    track_id: int,
    logger: LoggerProtocol | None = None,
) -> TrackFeatures | None:
    """
    Retrieves the features of an audio track.

    Args:
        track_id (int): The ID of the audio track to retrieve features for.
        logger (LoggerProtocol | None, optional):
            Logger instance.

    Returns:
        TrackFeatures | None:
            A dictionary containing the audio track's features,
            or None if no matching track is found.
    """
    logger = ensure_logger(logger, __name__)

    genre_columns_sql = get_genre_columns_sql()

    query = f"""
    SELECT
        bpm,
        initial_key,
        beat_intensity,
        mood_emb_1,
        mood_emb_2,
        genre_emb_1,
        genre_emb_2,
        duration,
        {genre_columns_sql}
    FROM audio_features
    WHERE id = ?
    """

    raw = select_one(query, (track_id,), logger=logger)

    if raw is None:
        logger.warning(
            "Aucune feature trouvée pour la track id=%s",
            track_id,
        )
        return None

    result: TrackFeatures = {
        "bpm": float(raw["bpm"]),
        "key": str(raw["initial_key"]),
        "beat_intensity": float(raw["beat_intensity"]),
        "mood_emb1": float(raw["mood_emb_1"]),
        "mood_emb2": float(raw["mood_emb_2"]),
        "genre_emb1": float(raw["genre_emb_1"]),
        "genre_emb2": float(raw["genre_emb_2"]),
        "genre_vector": build_genre_vector(cast(Mapping[str, object], raw)),
        "duration": float(raw["duration"]),
    }

    return result


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


def get_candidate_tracks(
    filters: MatchFilters, logger: LoggerProtocol | None = None
) -> list[CandidateTrack]:
    """
    Récupère les candidats compatibles avec les filtres demandés.
    """
    logger = ensure_logger(logger, __name__)

    genre_columns_sql = get_genre_columns_sql()
    genre_range = GENRE_BPM_RANGES.get(filters.genre)

    if genre_range is None:
        raise ValueError(f"Genre BPM range inconnu: {filters.genre}")

    where_clauses = [
        "af.id != ?",
        "af.bpm IS NOT NULL",
        "af.bpm BETWEEN ? AND ?",
        "af.initial_key IS NOT NULL",
        "af.beat_intensity IS NOT NULL",
        "af.duration IS NOT NULL",
        "af.duration > 0",
        "af.mood_emb_1 IS NOT NULL",
        "af.mood_emb_2 IS NOT NULL",
        "af.genre_emb_1 IS NOT NULL",
        "af.genre_emb_2 IS NOT NULL",
    ]

    params: list[object] = [
        filters.id_base,
        genre_range.min_bpm,
        genre_range.max_bpm,
    ]

    if not filters.include_live:
        where_clauses.append(
            """
            LOWER(COALESCE(i.albumtypes, '')) NOT LIKE '%live%'
            """
        )
        where_clauses.append(
            """
            LOWER(COALESCE(i.albumtypes, '')) NOT LIKE '%broadcast%'
            """
        )

    if filters.artist is not None and filters.artist.lower() != "all":
        where_clauses.append("LOWER(i.artist) = LOWER(?)")
        params.append(filters.artist)

    if filters.label is not None and filters.label.lower() != "all":
        where_clauses.append("LOWER(i.label) = LOWER(?)")
        params.append(filters.label)

    if filters.year_min is not None:
        where_clauses.append("i.year >= ?")
        params.append(filters.year_min)

    if filters.year_max is not None:
        where_clauses.append("i.year <= ?")
        params.append(filters.year_max)

    where_sql = "\n    AND ".join(where_clauses)

    query = f"""
    SELECT
        af.id,
        af.bpm,
        af.initial_key AS key,
        af.beat_intensity,
        af.mood_emb_1 AS mood_emb1,
        af.mood_emb_2 AS mood_emb2,
        af.genre_emb_1 AS genre_emb1,
        af.genre_emb_2 AS genre_emb2,
        af.duration,
        {genre_columns_sql},
        i.artist,
        i.label,
        i.year,
        i.albumtype
    FROM audio_features af
    JOIN items i ON i.id = af.id
    WHERE {where_sql};
    """

    try:
        rows = select_all(query, tuple(params), logger=logger)

        logger.debug("Nombre de candidats récupérés: %d", len(rows))
        logger.debug("Exemple de candidat: %r", rows[0] if rows else "Aucun")

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
                "genre_vector": build_genre_vector(cast(Mapping[str, object], row)),
                "duration": float(row["duration"]),
            }
            for row in rows
        ]

        return candidates

    except Exception as exc:  # pylint: disable=broad-except
        logger.error("Erreur lors de la récupération des candidats: %s", exc)
        return []


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
                    # logger.debug(
                    #     "RAW PATH CHECK | id=%s | row_path=%r | type=%s",
                    #     track_id,
                    #     row_map.get("path"),
                    #     type(row_map.get("path")),
                    # )
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

                            # logger.debug(
                            #     "Mapped path for track id=%s: %s",
                            #     track_id,
                            #     navidrome_path,
                            # )

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
