import sqlite3
from utils.config import MIX_DB, BEETS_DB

def get_connection(db_path: str = MIX_DB):
    return sqlite3.connect(db_path)

def execute_query(query: str, params: tuple = (), fetch: bool = False, db: str = MIX_DB):
    """Exécute une requête SQL sur la base spécifiée"""
    conn = get_connection(db)
    cursor = conn.cursor()
    cursor.execute(query, params)
    result = cursor.fetchall() if fetch else None
    conn.commit()
    conn.close()
    return result

def execute_many(query: str, param_list: list[tuple], db: str = MIX_DB):
    """Execute plusieurs requêtes en une transaction"""
    conn = get_connection(db)
    cursor = conn.cursor()
    cursor.executemany(query, param_list)
    conn.commit()
    conn.close()
