from datetime import datetime
from db.access import execute_query
from utils.config import BEETS_DB, EDM_GENRES
from utils.logger import get_logger

logname = __name__.split(".")[-1]

def fetch_beets_tracks_filtered(logname=logname):
    """Retourne les morceaux EDM valides depuis la base Beets"""
    logger = get_logger(logname)
    like_patterns = [f"%{g}%" for g in EDM_GENRES]
    conditions = " OR ".join(["lower(genre) LIKE ?"] * len(like_patterns))

    query = f"""
        SELECT id, title, artist, album, path, bpm, initial_key,
               rg_track_gain, genre, length
        FROM items
        WHERE ({conditions})
          AND bpm IS NOT NULL AND bpm > 0
          AND initial_key IS NOT NULL AND initial_key != ''
    """
    return execute_query(query, tuple(like_patterns), fetch=True, db=BEETS_DB, logname=logname)

def insert_track(data: dict, logname=logname) -> bool:
    logger = get_logger(logname)
    query = """
        INSERT OR IGNORE INTO tracks (
            beet_id, track_uid, title, artist, album, path,
            bpm, key, rg_gain, genre, length, added_at, updated_at, present_in_beets
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    try:
        params = (
            data["beet_id"], data["track_uid"], data["title"], data["artist"],
            data["album"], data["path"], data["bpm"], data["key"], data["rg_gain"],
            data["genre"], data["length"], data["added_at"], data["updated_at"], data["present_in_beets"]
        )
    
        inserted = execute_query(query, tuple(params), logname=logname)
        return inserted == 1  # True si insertion faite
    except Exception as e:
        raise