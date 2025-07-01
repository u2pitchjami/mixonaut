import sqlite3
import os
from utils.logger import get_logger, with_child_logger
from utils.config import BEETS_DB, LOCK_FILE
from beets_utils.beets_safe import safe_beets_call, read_lock_pid, get_current_pid

@with_child_logger
def get_connection(db_path: str = BEETS_DB, retries: int = 5, delay: int = 2, timeout: int = 10, logger=None):
    for attempt in range(retries):
        try:
            conn = sqlite3.connect(db_path, timeout=timeout)
            return conn
        except sqlite3.OperationalError as e:
            logger.warning(f"🔁 Tentative {attempt + 1}/{retries} : accès DB verrouillé → {e}")
            time.sleep(delay)
    logger.error(f"❌ Connexion à la base échouée après {retries} tentatives.")
    raise RuntimeError("Impossible d'obtenir une connexion à la base SQLite.")

@with_child_logger
def execute_query(query: str, params: tuple = (), fetch: bool = False,
                  db: str = BEETS_DB, logger: str = None):
    """Exécute une requête SQL sur la base spécifiée"""
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
            logger.warning("⚠️ Tentative de suppression du verrou non possédé (ignorée).")

def execute_many(query: str, param_list: list[tuple], db: str = BEETS_DB):
    """Execute plusieurs requêtes en une transaction"""
    conn = get_connection(db)
    cursor = conn.cursor()
    cursor.executemany(query, param_list)
    conn.commit()
    conn.close()

@with_child_logger
def select_all(query: str, params: tuple = (), db=BEETS_DB, logger=None):
    return execute_query(query, params=params, fetch=True, db=db, logger=logger)

@with_child_logger
def select_one(query: str, params: tuple = (), db=BEETS_DB, logger=None):
    result = execute_query(query, params=params, fetch=True, db=db, logger=logger)
    return result[0] if result else None

@with_child_logger
def execute_write(query: str, params: tuple = (), db=BEETS_DB, logger=None):
    return execute_query(query, params, fetch=False, db=db, logger=logger)

@with_child_logger
def select_scalar(query: str, params: tuple = (), db=BEETS_DB, logger=None):
    row = select_one(query, params, db=db, logger=logger)
    return row[0] if row else 0
