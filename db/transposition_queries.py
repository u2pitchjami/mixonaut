from datetime import datetime
from db.access import execute_query
from utils.config import BEETS_DB, EDM_GENRES
from utils.logger import get_logger, with_child_logger

@with_child_logger
def fetch_tracks_with_bpm_and_key(logger=None):
    query = "SELECT id, bpm, initial_key \
    FROM audio_features \
    WHERE bpm IS NOT NULL \
    AND bpm != 0 \
    AND initial_key IS NOT NULL \
    AND initial_key != 0"
    return execute_query(query, fetch=True, logger=logger)

@with_child_logger
def insert_transpositions(track_id, keys: dict, bpms: dict, logger: str = None):
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
