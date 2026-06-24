"""
20250820.

requetes sql pour la transpo
"""

import sqlite3
from typing import Any
from mixonaut.db.access import execute_query, select_one
from mixonaut.utils.logger import LoggerProtocol, ensure_logger


def fetch_tracks_with_bpm_and_key(
    logger: LoggerProtocol | None = None,
) -> list[sqlite3.Row]:
    """
    Récupère les tracks avec un BPM exploitable et une tonalité.

    BPM prioritaire : madmom puis audio_features.
    """
    logger = ensure_logger(logger, __name__)

    query = """
        SELECT
            a.id,
            a.initial_key,
            a.bpm AS essentia_bpm,

            m.bpm_main AS madmom_bpm,
            m.bpm_main_confidence,
            m.bpm_alt_1,
            m.bpm_alt_2

        FROM audio_features AS a
        LEFT JOIN madmom_features AS m
            ON m.id = a.id

        WHERE a.initial_key IS NOT NULL
          AND a.initial_key != ''
          AND a.initial_key != 'no_key'
          AND (
                a.bpm IS NOT NULL
             OR m.bpm_main IS NOT NULL
          )
    """

    return execute_query(query, fetch=True, logger=logger)


def get_bpm_context_by_id(
    track_id: int,
    logger: LoggerProtocol | None = None,
) -> dict[str, Any] | None:
    logger = ensure_logger(logger, __name__)

    query = """
        SELECT
            a.bpm AS essentia_bpm,

            m.bpm_main,
            m.bpm_main_confidence,

            m.bpm_alt_1,
            m.bpm_alt_1_confidence,

            m.bpm_alt_2,
            m.bpm_alt_2_confidence,

            m.rhythm_stability
        FROM audio_features AS a
        LEFT JOIN madmom_features AS m
            ON m.id = a.id
        WHERE a.id = ?
    """

    row = select_one(
        query,
        params=(track_id,),
        logger=logger,
    )

    if row is None:
        return None

    return dict(row)


def insert_transpositions(
    track_id: int,
    keys: dict[str, str],
    bpms: dict[str, float],
    logger: LoggerProtocol | None = None,
) -> None:
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
        INSERT OR REPLACE INTO track_transpositions ({", ".join(fields)})
        VALUES ({placeholders})
    """
    try:
        execute_query(query, tuple(values), logger=logger)
    except Exception as e:
        logger.error("Erreur d'insertion pour track_id %s : %s", track_id, e)
