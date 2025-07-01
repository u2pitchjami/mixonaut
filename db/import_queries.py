from db.access import select_all, select_one, execute_write
from utils.logger import get_logger, with_child_logger
import os
import time

@with_child_logger
def update_imported_file(path: str, size: int, logger=None):
    execute_write(
        "INSERT OR REPLACE INTO imported_files (path, size, last_seen) VALUES (?, ?, ?)",
        (path, size, time.time()),
        logger=logger
    )

@with_child_logger
def cleanup_imported_files(base_folder: str, logger=None):
    rows = select_all("SELECT path FROM imported_files", logger=logger)
    for (path,) in rows:
        full_path = os.path.join(base_folder, os.path.relpath(path, base_folder))
        if not os.path.exists(full_path):
            execute_write("DELETE FROM imported_files WHERE path = ?", (path,), logger=logger)
            logger.info(f"Supprimé de la base de suivi (plus présent): {path}")

@with_child_logger
def is_already_imported(path: str, size: int, logger=None):
    res = select_one("SELECT size FROM imported_files WHERE path = ?", (path,), logger=logger)
    return res and res[0] == size

@with_child_logger
def insert_or_update_imported(path: str, size: int, logger=None):
    execute_write(
        "INSERT OR REPLACE INTO imported_files (path, size, last_seen) VALUES (?, ?, ?)",
        (path, size, time.time()),
        logger=logger
    )

@with_child_logger
def cleanup_missing_imported(logger=None):
    rows = select_all("SELECT path FROM imported_files", logger=logger)
    for (tracked_path,) in rows:
        if not os.path.exists(tracked_path):
            execute_write("DELETE FROM imported_files WHERE path = ?", (tracked_path,), logger=logger)
            logger.info(f"Fichier disparu supprimé du suivi : {tracked_path}")