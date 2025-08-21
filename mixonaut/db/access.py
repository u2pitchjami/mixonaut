import sqlite3
import os
from utils.logger import with_child_logger
from utils.config import BEETS_DB, LOCK_FILE
from beets_utils.lock.beets_safe import safe_beets_call, read_lock_pid, get_current_pid

@with_child_logger
def get_connection(db_path: str = BEETS_DB, retries: int = 20, delay: int = 5, timeout: int = 30, logger=None):
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

@with_child_logger
def execute_many(query: str,
                 param_list: list[tuple],
                 db: str = BEETS_DB,
                 logger=None) -> None:
    """
    Exécute la même requête SQL pour une liste de paramètres dans UNE transaction.
    - Respecte le verrou (safe_beets_call)
    - Journalise les erreurs
    - Commit/rollback atomique
    """
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
            logger.warning("⚠️ Tentative de suppression du verrou non possédé (ignorée).")

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
