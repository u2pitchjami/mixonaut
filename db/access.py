import sqlite3
from utils.logger import get_logger
from utils.config import BEETS_DB

logname = __name__.split(".")[-1]

def get_connection(db_path: str = BEETS_DB):
    return sqlite3.connect(db_path)

def execute_query(query: str, params: tuple = (), fetch: bool = False, db: str = BEETS_DB, logname: str = logname):
    """Exécute une requête SQL sur la base spécifiée"""
    logger = get_logger(logname)
    try:
        conn = get_connection(db)
    except sqlite3.Error as e:
        logger.error(f"❌ [{__name__.split(".")[-1]}] Erreur dans la connexion à la base → {e}")
        raise
    try:
        cursor = conn.cursor()
        cursor.execute(query, params)
        result = cursor.fetchall() if fetch else None
        conn.commit()
        conn.close()
        return result
    except sqlite3.Error as e:
        logger.error(f"❌ [{__name__.split(".")[-1]}] Erreur dans l'exécution de la requête → {e}")
        conn.rollback()
        conn.close()
        raise
    

def execute_many(query: str, param_list: list[tuple], db: str = BEETS_DB):
    """Execute plusieurs requêtes en une transaction"""
    conn = get_connection(db)
    cursor = conn.cursor()
    cursor.executemany(query, param_list)
    conn.commit()
    conn.close()
