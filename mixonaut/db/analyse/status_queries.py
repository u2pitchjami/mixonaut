"""
20250820.

requetes sqlite gère les statuts pour lancer ou non l'analyse.
"""

from datetime import datetime

from mixonaut.db.access import execute_many, execute_write, select_all
from mixonaut.utils.logger import LoggerProtocol, ensure_logger, with_child_logger


@with_child_logger
def update_table_status(
    table: str,
    id_value: int,
    status: str,
    last_error: str | None = None,
    logger: LoggerProtocol | None = None,
) -> None:
    """
    Met à jour le statut + last_error.

    Horodatage via SQLite: CURRENT_TIMESTAMP (UTC, 'YYYY-MM-DD HH:MM:SS').
    """
    logger = ensure_logger(logger, __name__)
    status_col = get_status_column(table)
    query = f"""
        UPDATE {table}
        SET {status_col} = ?,
            last_error = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """
    execute_write(query, (status, last_error, id_value), logger=logger)


def get_status_column(table: str) -> str:
    """
    Retourne le nom exact de la colonne 'status' pour la table donnée.

    Permet d'éviter les hardcodes et de gérer audio_features/transpositions différemment.
    """
    if table == "audio_features":
        return "essentia_status"
    elif table == "track_transpositions":
        return "transposition_status"
    elif table == "audio_hash":
        return "status"
    else:
        raise ValueError(f"Table inconnue pour mise à jour de statut : {table}")


@with_child_logger
def sync_pending_tables(logger: LoggerProtocol | None = None):
    """
    Synchronise les tables pending en ajoutant des enregistrements manquants.

    Ce fonctionnalité est destinée à ajouter des enregistrements dans les tables audio_features,
    track_transpositions et audio_hash qui ne sont pas encore dans la base de données SQLite.

    Elle utilise les requêtes SQL suivantes :

    - Récupérer les IDs d'items absents de chaque table.
    - Ajouter ces items à leur tableau correspondant avec statut par défaut 'PENDING'.
    """
    logger = ensure_logger(logger, __name__)
    now = datetime.utcnow().isoformat(timespec="seconds")

    # Tables à synchroniser : table, colonne statut, statut par défaut
    tables = [
        ("audio_features", "essentia_status", "PENDING"),
        ("track_transpositions", "transposition_status", "PENDING"),
        ("audio_hash", "status", "PENDING"),  # statut défaut pour fp_links
    ]

    for table, status_col, default_status in tables:
        # Récupérer les items absents de la table
        missing_items = select_all(
            f"""
            SELECT id FROM items
            WHERE id NOT IN (SELECT id FROM {table})
            """,
            logger=logger,
        )

        if not missing_items:
            logger.info(f"✅ Rien à créer pour {table} (déjà complet).")
            continue

        logger.info(f"➕ {len(missing_items)} enregistrements à insérer dans {table}.")

        # Préparer les valeurs à insérer
        param_list = []
        for (item_id,) in missing_items:
            # fp_links n'a pas last_error si déjà dans ton schéma
            param_list.append((item_id, default_status, None, now))

        # Construire la requête d'INSERT
        query = f"""
            INSERT OR IGNORE INTO {table} (id, {status_col}, last_error, updated_at)
            VALUES (?, ?, ?, ?)
        """
        execute_many(query, param_list, logger=logger)

        logger.info(f"✅ {len(param_list)} lignes ajoutées dans {table}.")


# if __name__ == "__main__":

#     logger = get_logger(__name__)
#     sync_pending_tables(logger=logger)
