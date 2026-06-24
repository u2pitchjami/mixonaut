"""
2025-08-20.

requêtes sqlite beets
"""

from typing import Any

from mixonaut.db.access import execute_query, execute_write, select_all, select_one
from mixonaut.utils.logger import LoggerProtocol, ensure_logger


def get_item_field_value(
    field: str, track_id: int, logger: LoggerProtocol | None = None
) -> Any | None:
    """
    Récupère la valeur d'un champ donné pour un item spécifique.

    :param field: Le nom du champ à interroger (ex: 'genre', 'bpm', etc.)
    :param track_id: L'identifiant de la ligne dans la table 'items'
    :return: La valeur du champ ou None si introuvable
    """
    logger = ensure_logger(logger, __name__)
    try:
        query = f"SELECT {field} FROM items WHERE id = ?"
        result = execute_query(query, (track_id,), fetch=True, logger=logger)
        return result[0][0] if result else None
    except Exception as e:
        raise ValueError(
            f"Erreur lors de la récupération du champ '{field}' pour ID {track_id}"
        ) from e


def get_items_columns(logger: LoggerProtocol | None = None) -> set[str]:
    """
    Récupère l'ensemble des colonnes de la table 'items'.

    :return: Une collection contenant les noms des colonnes
    """
    logger = ensure_logger(logger, __name__)
    columns_info = select_all("PRAGMA table_info(items)", logger=logger)
    return {col[1] for col in columns_info}


def retro_inject_features(
    track_id: int,
    features: dict[str, Any],
    items_columns: set[str],
    logger: LoggerProtocol | None = None,
) -> None:
    """
    Injecte des valeurs de fonctionnalités dans la base de données pour un track spécifique.

    :param track_id: L'identifiant de la ligne dans la table 'items'
    :param features: Un dictionnaire contenant les clés et leurs valeurs à injecter
    :param items_columns: Une collection contenant les noms des colonnes relevant de l'item
    :param logger: Un objet logique (ou aucun, par défaut)
    """
    logger = ensure_logger(logger, __name__)
    try:
        # Sépare les données d'items et d'attributs
        items_data = {k: v for k, v in features.items() if k in items_columns}
        attributes_data = {k: v for k, v in features.items() if k not in items_columns}

        # Met à jour les valeurs des champs de l'item
        if items_data:
            set_clause = ", ".join([f"{k} = ?" for k in items_data.keys()])
            params = list(items_data.values()) + [track_id]
            query = f"UPDATE items SET {set_clause} WHERE id = ?"
            execute_write(query, tuple(params), logger=logger)

        # Met à jour ou insertion des attributs
        for key, value in attributes_data.items():
            result = select_one(
                "SELECT id FROM item_attributes WHERE entity_id = ? AND key = ?",
                (track_id, key),
                logger=logger,
            )

            if result:
                execute_write(
                    "UPDATE item_attributes SET value = ? WHERE id = ?",
                    (value, result[0]),
                    logger=logger,
                )
            else:
                execute_write(
                    "INSERT INTO item_attributes (entity_id, key, value) VALUES (?, ?, ?)",
                    (track_id, key, value),
                    logger=logger,
                )

    except Exception as e:
        logger.exception(
            f"Erreur lors de l'injection des features pour track_id={track_id}: {e}"
        )
        raise
