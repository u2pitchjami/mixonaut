from db.access import execute_query
from utils.logger import get_logger

def fetch_data_in_mixonaut_by_beet_id(fields="mood", table="tracks", beet_id=None, logname="Mixonaut"):
    logger = get_logger(logname)

    if beet_id is None:
        logger.warning("beet_id absent, requête annulée.")
        return {"status": "invalid", "values": None}

    try:
        query = f"SELECT {fields} FROM {table} WHERE beet_id = ?"
        params = (beet_id,)
        result = execute_query(query, params, fetch=True)

        if not result:
            return {"status": "not_found", "values": None}

        row = result[0]
        # Vérifie si au moins un champ est vide ou tous pleins
        if all(val is None or str(val).strip() == "" for val in row):
            return {"status": "empty", "values": row}

        return {"status": "ok", "values": row}

    except Exception as e:
        logger.error(f"Erreur SQL (beet_id={beet_id}) : {e}")
        return {"status": "error", "values": None}

