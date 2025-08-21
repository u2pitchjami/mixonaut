"""
2025-08-21 sql queries for matching.
"""

from mixonaut.db.access import select_all, select_one
from mixonaut.utils.logger import LoggerProtocol, ensure_logger, with_child_logger


@with_child_logger
def get_track_features(
    track_id: int, logger: LoggerProtocol | None = None
) -> tuple | None:
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
    return select_one(query, (track_id,), logger=logger)


@with_child_logger
def get_transpositions(
    track_id: int, logger: LoggerProtocol | None = None
) -> tuple | None:
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
) -> list[tuple]:
    """
    Retrieves a list of candidate tracks that do not match the provided track ID.

    Args:
        track_id (int): The ID of the track to exclude from the results.

    Returns:
        list[tuple]: A list of tuples containing information about the candidate tracks.
    """
    logger = ensure_logger(logger, __name__)
    query = """
    SELECT id, bpm, initial_key, beat_intensity, mood_emb_1, mood_emb_2, genre_emb_1, genre_emb_2, duration
    FROM audio_features
    WHERE id != ?
    """
    return select_all(query, (track_id,), logger=logger)


@with_child_logger
def enrich_matches_with_metadata(
    matches: list[dict], logger: LoggerProtocol | None = None
) -> list[dict]:
    """
    Enhance track matches with metadata from the 'items' table.

    This function iterates over a list of track matches and retrieves corresponding artist, album, and title information
    for each match. If no matching row is found in the 'items' table, default values ('Unknown') are assigned to the
    corresponding metadata fields.

    Args:
        matches (list[dict]): A list of dictionaries representing track matches.
        logger (str, optional): The logger instance used for logging. Defaults to None.

    Returns:
        list[dict]: The enriched list of track matches with added metadata.
    """
    logger = ensure_logger(logger, __name__)
    for match in matches:
        row = select_one(
            "SELECT artist, album, title FROM items WHERE id = ?",
            (match["track_id"],),
            logger=logger,
        )
        if row:
            match["artist"], match["album"], match["title"] = row
        else:
            match["artist"], match["album"], match["title"] = (
                "Unknown",
                "Unknown",
                "Unknown",
            )
    return matches
