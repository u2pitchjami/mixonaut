import sqlite3
from utils.logger import get_logger
from utils.config import BEETS_DB

logname = __name__.split(".")[-1]

def get_connection(db_path: str = BEETS_DB):
    return sqlite3.connect(db_path)

def execute_query(query: str, params: tuple = (), fetch: bool = False,
                  db: str = BEETS_DB, logname: str = logname):
    """Exécute une requête SQL sur la base spécifiée"""
    logger = get_logger(logname)
    try:
        conn = get_connection(db)
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
        conn.close()

def execute_many(query: str, param_list: list[tuple], db: str = BEETS_DB):
    """Execute plusieurs requêtes en une transaction"""
    conn = get_connection(db)
    cursor = conn.cursor()
    cursor.executemany(query, param_list)
    conn.commit()
    conn.close()

def select_all(query: str, params: tuple = (), db=BEETS_DB, logname=None):
    return execute_query(query, params=params, fetch=True, db=db, logname=logname)

def select_one(query: str, params: tuple = (), db=BEETS_DB, logname=None):
    result = execute_query(query, params=params, fetch=True, db=db, logname=logname)
    return result[0] if result else None

def execute_write(query: str, params: tuple = (), db=BEETS_DB, logname=None):
    return execute_query(query, params, fetch=False, db=db, logname=logname)

def select_scalar(query: str, params: tuple = (), db=BEETS_DB, logname=None):
    row = select_one(query, params, db=db, logname=logname)
    return row[0] if row else 0
