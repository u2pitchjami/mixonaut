from datetime import datetime
from db.access import execute_query
from utils.config import BEETS_DB, EDM_GENRES
from utils.logger import get_logger

def fetch_tracks_with_bpm_and_key():
    query = "SELECT id, bpm, key FROM tracks WHERE bpm IS NOT NULL AND key IS NOT NULL"
    return execute_query(query, fetch=True)

def insert_transpositions(track_id, keys: dict, bpms: dict, logname="Mix_Assist"):

    logger = get_logger(logname)
    
    fields = ["track_id"] + list(keys.keys()) + list(bpms.keys())
    values = [track_id] + list(keys.values()) + list(bpms.values())
    placeholders = ", ".join(["?"] * len(values))
    query = f"""
        INSERT OR REPLACE INTO track_transpositions ({', '.join(fields)})
        VALUES ({placeholders})
    """
    try:
        execute_query(query, tuple(values))
    except Exception as e:
        logger.error("Erreur d'insertion pour track_id %s : %s", track_id, e)
