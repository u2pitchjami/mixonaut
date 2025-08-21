"""
20250820.

requetes sql pour la transpo
"""

from mixonaut.db.access import execute_query
from mixonaut.utils.logger import LoggerProtocol, ensure_logger, with_child_logger


@with_child_logger
def fetch_tracks_with_bpm_and_key(logger: LoggerProtocol | None = None):
    """
    Fetch tracks from the audio_features table that have a valid BPM and key.

    Args:
        logger (LoggerProtocol, optional): The logger to use for logging. Defaults to None.

    Returns:
        list: A list of dictionaries containing the track id, BPM, and initial key.
    """
    logger = ensure_logger(logger, __name__)
    query = "SELECT id, bpm, initial_key \
    FROM audio_features \
    WHERE bpm IS NOT NULL \
    AND bpm != 0 \
    AND initial_key IS NOT NULL \
    AND initial_key != 0"
    return execute_query(query, fetch=True, logger=logger)


@with_child_logger
def insert_transpositions(
    track_id, keys: dict, bpms: dict, logger: LoggerProtocol | None = None
):
    """
    Insert a new track transposition or replace an existing one.
    Args:
        track_id (int): The ID of the track to transpose.
        keys (dict): A dictionary containing the key information.
        bpms (dict): A dictionary containing the BPM information.
        logger (str, optional): An optional logger instance. Defaults to None.

    Raises:
        Exception: If an error occurs during insertion.
    """
    logger = ensure_logger(logger, __name__)
    fields = ["id"] + list(keys.keys()) + list(bpms.keys())
    values = [track_id] + list(keys.values()) + list(bpms.values())
    placeholders = ", ".join(["?"] * len(values))
    query = f"""
        INSERT OR REPLACE INTO track_transpositions ({', '.join(fields)})
        VALUES ({placeholders})
    """
    try:
        execute_query(query, tuple(values), logger=logger)
    except Exception as e:
        logger.error("Erreur d'insertion pour track_id %s : %s", track_id, e)
