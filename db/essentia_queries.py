from datetime import datetime
from db.access import execute_query
from db.db_utils import ensure_columns_exist
from utils.config import BEETS_DB, EDM_GENRES
from utils.logger import get_logger

def fetch_tracks_missing_essentia(force: bool = False):
    base_fields = "id, path, artist, album, title, beet_id"
    try:
        if force:
            query = f"SELECT {base_fields} FROM tracks"
            params = ()
        else:
            query = f"""
            SELECT {base_fields} FROM tracks
            WHERE beat_intensity IS NULL 
            OR energy_level IS NULL
            """
            params = ()

        return execute_query(query, params, fetch=True)
    except Exception as e:
        raise

def insert_or_update_audio_features(track_id: int, features: dict, force=True, logname="Mixonaut"):
    logger = get_logger(logname)
    try:
        if not features:
            logger.warning("Aucune feature fournie pour audio_features.")
            return

        features_cleaned = {k: v for k, v in features.items() if v is not None}
        if not features_cleaned:
            logger.warning("Aucun champ valide pour audio_features.")
        
            
        #ensure_columns_exist(table="audio_features", columns=features_cleaned, logname=logname)
        check_query = "SELECT id FROM audio_features WHERE track_id = ?"
        exists = execute_query(check_query, (track_id,), fetch=True)

        field_list = ", ".join(features_cleaned.keys())
        placeholders = ", ".join("?" for _ in features_cleaned)
        values = list(features_cleaned.values())

        if exists:
            # UPDATE
            if force:
                assignments = ", ".join(f"{k} = ?" for k in features_cleaned)
            else:
                assignments = ", ".join(f"{k} = CASE WHEN {k} IS NULL THEN ? ELSE {k} END" for k in features_cleaned)

            update_query = f"""
                UPDATE audio_features
                SET {assignments}
                WHERE track_id = ?
            """
            execute_query(update_query, tuple(values + [track_id]))

        else:
            # INSERT
            insert_query = f"""
                INSERT INTO audio_features (track_id, {field_list})
                VALUES (?, {placeholders})
            """
            execute_query(insert_query, tuple([track_id] + values))

    except Exception as e:
        raise
