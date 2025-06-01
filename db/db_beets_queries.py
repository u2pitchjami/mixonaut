from db.access import execute_query
from utils.config import BEETS_DB, EDM_GENRES
from utils.logger import get_logger

def get_item_field_value(field: str, track_id: int) -> any:
    """
    Récupère la valeur d'un champ donné pour un item spécifique.
    
    :param field: Le nom du champ à interroger (ex: 'genre', 'bpm', etc.)
    :param track_id: L'identifiant de la ligne dans la table 'items'
    :return: La valeur du champ ou None si introuvable
    """
    try:
        query = f"SELECT {field} FROM items WHERE id = ?"
        result = execute_query(query, (track_id,), fetch=True)
        return result[0][0] if result else None
    except Exception as e:
        raise ValueError(f"Erreur lors de la récupération du champ '{field}' pour ID {track_id}") from e
