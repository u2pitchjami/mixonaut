from db.access import execute_query, select_all, select_one, execute_write
from utils.config import BEETS_DB, EDM_GENRES
from utils.logger import get_logger, with_child_logger

@with_child_logger
def get_item_field_value(field: str, track_id: int, logger: str = None) -> any:
    """
    Récupère la valeur d'un champ donné pour un item spécifique.
    
    :param field: Le nom du champ à interroger (ex: 'genre', 'bpm', etc.)
    :param track_id: L'identifiant de la ligne dans la table 'items'
    :return: La valeur du champ ou None si introuvable
    """
    try:
        query = f"SELECT {field} FROM items WHERE id = ?"
        result = execute_query(query, (track_id,), fetch=True, logger=logger)
        return result[0][0] if result else None
    except Exception as e:
        raise ValueError(f"Erreur lors de la récupération du champ '{field}' pour ID {track_id}") from e

@with_child_logger
def get_items_columns(logger=None):
    columns_info = select_all("PRAGMA table_info(items)", logger=logger)
    return {col[1] for col in columns_info}

@with_child_logger
def retro_inject_features(track_id: int, features: dict, items_columns: set, logger=None):
    try:
        items_data = {k: v for k, v in features.items() if k in items_columns}
        attributes_data = {k: v for k, v in features.items() if k not in items_columns}

        if items_data:
            set_clause = ', '.join([f"{k} = ?" for k in items_data.keys()])
            params = list(items_data.values()) + [track_id]
            query = f"UPDATE items SET {set_clause} WHERE id = ?"
            execute_write(query, tuple(params), logger=logger)

        for key, value in attributes_data.items():
            result = select_one(
                "SELECT id FROM item_attributes WHERE entity_id = ? AND key = ?",
                (track_id, key),
                logger=logger
            )

            if result:
                execute_write(
                    "UPDATE item_attributes SET value = ? WHERE id = ?",
                    (value, result[0]),
                    logger=logger
                )
            else:
                execute_write(
                    "INSERT INTO item_attributes (entity_id, key, value) VALUES (?, ?, ?)",
                    (track_id, key, value),
                    logger=logger
                )

    except Exception as e:
        logger.exception(f"Erreur lors de l'injection des features pour track_id={track_id}: {e}")
        raise
