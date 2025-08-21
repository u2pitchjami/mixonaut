"""2025-08-21 - modules d'accés à la base sqlite"""

import os
import sqlite3
import time

from mixonaut.beets_utils.lock.beets_safe import (
    get_current_pid,
    read_lock_pid,
    safe_beets_call,
)
from mixonaut.utils.config import BEETS_DB, LOCK_FILE
from mixonaut.utils.logger import LoggerProtocol, ensure_logger, with_child_logger


@with_child_logger
def get_connection(
    db_path: str = BEETS_DB,
    retries: int = 20,
    delay: int = 5,
    timeout: int = 30,
    logger: LoggerProtocol | None = None,
):
    """
    Attempts to establish a connection to the Beets SQLite database.

    Args:
        db_path (str): The path to the Beets SQLite database file.
            Defaults to BEETS_DB if not provided.
        retries (int): The maximum number of attempts to establish a connection.
            Defaults to 20 if not provided.
        delay (int): The interval in seconds between attempts to establish a connection.
            Defaults to 5 if not provided.
        timeout (int): The timeout in seconds for the database connection attempt.
            Defaults to 30 if not provided.
        logger: A logging object. If not provided, a child logger will be created.

    Returns:
        sqlite3.Connection: A connection to the Beets SQLite database.

    Raises:
        RuntimeError: If all attempts to establish a connection fail.
    """
    logger = ensure_logger(logger, __name__)
    for attempt in range(retries):
        try:
            conn = sqlite3.connect(db_path, timeout=timeout)
            return conn
        except sqlite3.OperationalError as e:
            logger.warning(
                f"🔁 Tentative {attempt + 1}/{retries} : accès DB verrouillé → {e}"
            )
            time.sleep(delay)
    logger.error(f"❌ Connexion à la base échouée après {retries} tentatives.")
    raise RuntimeError("Impossible d'obtenir une connexion à la base SQLite.")


@with_child_logger
def execute_query(
    query: str,
    params: tuple = (),
    fetch: bool = False,
    db: str = BEETS_DB,
    logger: LoggerProtocol | None = None,
):
    """
    Exécute une requête SQL sur la base spécifiée.
    """
    logger = ensure_logger(logger, __name__)
    try:
        conn = False
        if safe_beets_call(logger=logger):
            conn = get_connection(db, logger=logger)
    except sqlite3.Error as e:
        logger.error(f"❌ [{__name__.split('.')[-1]}] Erreur connexion DB → {e}")
        raise
    try:
        cursor = conn.cursor()
        cursor.execute(query, params)
        result = cursor.fetchall() if fetch else None
        conn.commit()
        return result
    except sqlite3.Error as e:
        logger.error(f"❌ [{__name__.split('.')[-1]}] Erreur exécution requête → {e}")
        conn.rollback()
        raise
    finally:
        if conn:
            conn.close()
        if read_lock_pid() == get_current_pid():
            os.remove(LOCK_FILE)
            logger.debug("🔓 Verrou supprimé.")
        else:
            logger.warning(
                "⚠️ Tentative de suppression du verrou non possédé (ignorée)."
            )


@with_child_logger
def execute_many(
    query: str,
    param_list: list[tuple],
    db: str = BEETS_DB,
    logger: LoggerProtocol | None = None,
) -> None:
    """
    Exécute la même requête SQL pour une liste de paramètres dans UNE transaction.

    - Respecte le verrou (safe_beets_call)
    - Journalise les erreurs
    - Commit/rollback atomique
    """
    logger = ensure_logger(logger, __name__)
    if not param_list:
        logger.debug("execute_many: rien à exécuter (param_list vide)")
        return

    try:
        conn = None
        if safe_beets_call(logger=logger):
            conn = sqlite3.connect(db, timeout=30)
        else:
            raise sqlite3.OperationalError("safe_beets_call a refusé l'accès à la DB")
    except sqlite3.Error as exc:
        logger.error("❌ [access] Erreur connexion DB → %s", exc)
        raise

    try:
        cur = conn.cursor()
        # Une seule transaction englobante (bien plus rapide)
        cur.executemany(query, param_list)
        conn.commit()
        logger.debug("execute_many: %d lignes écrites", len(param_list))
    except sqlite3.Error as exc:
        logger.error("❌ [access] Erreur execute_many → %s", exc)
        conn.rollback()
        raise
    finally:
        if conn:
            conn.close()
        # Gestion du verrou comme dans execute_query
        if read_lock_pid() == get_current_pid():
            try:
                os.remove(LOCK_FILE)
                logger.debug("🔓 Verrou supprimé.")
            except OSError:
                logger.debug("🔓 Verrou déjà absent.")
        else:
            logger.warning(
                "⚠️ Tentative de suppression du verrou non possédé (ignorée)."
            )


@with_child_logger
def select_all(
    query: str, params: tuple = (), db=BEETS_DB, logger: LoggerProtocol | None = None
):
    """
    Execute a query to retrieve all rows.

    Args:
        query (str): The SQL query to execute.
        params (tuple, optional): Parameters for the query. Defaults to () if not provided.
        db (str, optional): The path to the SQLite database file. Defaults to BEETS_DB.
        logger: A logging object. If not provided, a child logger will be created.

    Returns:
        list: A list of tuples containing all rows from the result set.
    """
    logger = ensure_logger(logger, __name__)
    return execute_query(query, params=params, fetch=True, db=db, logger=logger)


@with_child_logger
def select_one(
    query: str, params: tuple = (), db=BEETS_DB, logger: LoggerProtocol | None = None
):
    """
    Execute a query to retrieve one row.

    Args:
        query (str): The SQL query to execute.
        params (tuple, optional): Parameters for the query. Defaults to () if not provided.
        db (str, optional): The path to the SQLite database file. Defaults to BEETS_DB.
        logger: A logging object. If not provided, a child logger will be created.

    Returns:
        tuple or None: A single row from the result set, or None if no rows are found.

    Raises:
        RuntimeError: If any error occurs during execution.
    """
    logger = ensure_logger(logger, __name__)
    result = execute_query(query, params=params, fetch=True, db=db, logger=logger)
    return result[0] if result else None


@with_child_logger
def execute_write(
    query: str, params: tuple = (), db=BEETS_DB, logger: LoggerProtocol | None = None
):
    """
    Execute une requête d'écriture sur la base spécifiée.

    Args:
        query (str): La requête SQL à exécuter.
        params (tuple): Les paramètres de la requête SQL.
        db (str): Le chemin vers le fichier de base SQLite.
            Defaults to BEETS_DB if not provided.
        logger: Un objet de journalisation. Si pas fourni, un child logger sera créé.

    Returns:
        None

    Raises:
        RuntimeError: Si une erreur se produit pendant l'exécution de la requête.
    """
    logger = ensure_logger(logger, __name__)
    return execute_query(query, params, fetch=False, db=db, logger=logger)


@with_child_logger
def select_scalar(
    query: str, params: tuple = (), db=BEETS_DB, logger: LoggerProtocol | None = None
):
    """
    Execute a single SELECT query and return the first column.

    Args:
        query (str): The SQL query to execute.
        params (tuple): A tuple of parameters for the query.
        db (str): The path to the Beets SQLite database file. Defaults to BEETS_DB.
        logger: A logging object. If not provided, a child logger will be created.

    Returns:
        The first column of the result row, or None if no rows are returned.

    Raises:
        sqlite3.Error: If an error occurs during query execution.
    """
    logger = ensure_logger(logger, __name__)
    row = select_one(query, params, db=db, logger=logger)
    return row[0] if row else 0
