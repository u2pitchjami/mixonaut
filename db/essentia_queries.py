from datetime import datetime
from db.access import execute_query, select_one, select_scalar, select_all
from utils.config import BEETS_DB, EDM_GENRES
from utils.logger import get_logger

def get_all_track_ids():
    rows = select_all("SELECT id FROM audio_features", (), logname=__name__)
    return [row[0] for row in rows]

def fetch_tracks(missing_features=False, is_edm=False, missing_field=None, path_contains=None):
    base_query = """
    SELECT i.id, i.path, i.artist, i.album, i.title
    FROM items i
    LEFT JOIN audio_features af ON i.id = af.id
    """
    where_clauses = []
    params = []

    if missing_features:
        where_clauses.append("af.id IS NULL")

    if missing_field:
        allowed_fields = {"bpm", "energy_level", "mood", "beat_intensity", "initial_key", "rg_track_gain", "genre"}
        if missing_field not in allowed_fields:
            raise ValueError(f"Champ interdit : {missing_field}")
        where_clauses.append(f"(i.{missing_field} IS NULL OR i.{missing_field} = '')")

    if path_contains:
        where_clauses.append("i.path LIKE ?")
        params.append(f"%{path_contains}%")

    if is_edm:
        edm_clauses = [f"i.genre LIKE ?" for _ in EDM_GENRES]
        where_clauses.append(f"({' OR '.join(edm_clauses)})")
        params.extend([f"%{genre}%" for genre in EDM_GENRES])

    if where_clauses:
        base_query += " WHERE " + " AND ".join(where_clauses)

    try:
        return execute_query(base_query, tuple(params), fetch=True)
    except Exception as e:
        logger.error(f"Erreur dans fetch_tracks : {e}")
        raise

def insert_or_update_audio_features(item_id: int, features: dict, force=True, logname="Mixonaut"):
    logger = get_logger(logname)
    
    try:
        if not features:
            logger.warning("Aucune feature fournie pour audio_features.")
            return False

        features_cleaned = {k: v for k, v in features.items() if v is not None}

        if not features_cleaned:
            logger.warning("Aucun champ valide pour audio_features.")
            return False

        # Vérifie si la ligne existe déjà
        check_query = "SELECT id FROM audio_features WHERE id = ?"
        exists = execute_query(check_query, (item_id,), fetch=True)

        field_list = ", ".join(features_cleaned.keys())
        placeholders = ", ".join("?" for _ in features_cleaned)
        values = list(features_cleaned.values())

        
        if exists:
            if force:
                assignments = ", ".join(f"{k} = ?" for k in features_cleaned)
            else:
                assignments = ", ".join(f"{k} = CASE WHEN {k} IS NULL THEN ? ELSE {k} END" for k in features_cleaned)

            update_query = f"""
                UPDATE audio_features
                SET {assignments}
                WHERE id = ?
            """
            #logger.debug(f"[UPDATE] {update_query} {values + [item_id]}")
            execute_query(update_query, tuple(values + [item_id]))

        else:
            insert_query = f"""
                INSERT INTO audio_features (id, {field_list})
                VALUES (?, {placeholders})
            """
            #logger.debug(f"[INSERT] {insert_query} {[item_id] + values}")
            execute_query(insert_query, tuple([item_id] + values))

        return True

    except Exception as e:
        logger.error(f"Erreur dans insert_or_update_audio_features pour ID {item_id} : {e}")
        raise

def get_audio_features_by_id(track_id: int) -> dict:
    query = "SELECT * FROM audio_features WHERE id = ?"
    rows = execute_query(query, (track_id,), fetch=True)

    if not rows:
        return None

    row = rows[0]  # On suppose un seul résultat

    # Obtenir les noms de colonnes (si execute_query ne le fait pas)
    columns_query = "PRAGMA table_info(audio_features)"
    columns_info = execute_query(columns_query, (), fetch=True)
    column_names = [col[1] for col in columns_info]  # col[1] = name

    return dict(zip(column_names, row))

def nb_query(table: str = "audio_features") -> dict:
    query = f"SELECT * FROM {table}"
    rows = execute_query(query, (), fetch=True)

    if not rows:
        return None

    nb = len(rows)

    return nb

def count_existing_features(track_ids: list[int], logname="Mixonaut") -> int:
    logger = get_logger(logname)
    """
    Retourne le nombre de tracks présents dans audio_features pour les ids fournis.
    """
    if not track_ids:
        return 0
    
    placeholders = ','.join(['?'] * len(track_ids))
    query = f"SELECT COUNT(*) FROM audio_features WHERE id IN ({placeholders})"
    
    try:
        result = select_one(query, params=tuple(track_ids), logname=logname)
        return result[0] if result else 0
    except Exception as e:
        logger.error(f"Erreur dans count_existing_features : {e}")
        return 0
