from db.access import select_all, select_one, execute_write, select_scalar
from utils.logger import with_child_logger
import os
import time

@with_child_logger
def get_imported_music_files(logger=None):
    query = """
    SELECT path, import_date
    FROM imported_files
    """
    return select_all(query, logger=logger)

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
def is_already_imported(name: str, torrent_name: str, logger=None) -> bool:
    """
    Vérifie si un fichier a déjà été importé par Beets,
    via son nom et le nom du torrent (ou via path), et marqué comme importé.
    """
    # 🔍 Méthode 1 : correspondance stricte
    row = select_one(
        """
        SELECT 1 FROM imported_files
        WHERE name = ? AND torrent_name = ? AND imported_in_beets_at IS NOT NULL
        LIMIT 1
        """,
        (name, torrent_name),
        logger=logger
    )

    if row:
        return True

    # 🔍 Méthode 2 : recherche partielle dans path (fallback)
    like_clause = f"%{torrent_name}%{name}"
    row = select_one(
        """
        SELECT 1 FROM imported_files
        WHERE path LIKE ? AND imported_in_beets_at IS NOT NULL
        LIMIT 1
        """,
        (like_clause,),
        logger=logger
    )

    return bool(row)

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

@with_child_logger
def update_imported_in_beets_at(torrent_name: str, logger=None) -> bool:
    """
    Marque comme importés tous les fichiers liés à un torrent donné.
    :param torrent_name: nom du dossier torrent (ex: "U2-BoxSet")
    :return: True si au moins un fichier a été mis à jour
    """
    logger.info(f"🔍 Mise à jour des fichiers pour torrent_name = {torrent_name}")
    
    count = select_scalar(
        "SELECT COUNT(*) FROM imported_files WHERE torrent_name = ? AND imported_in_beets_at IS NULL",
        (torrent_name,),
        logger=logger
    )

    if count == 0:
        logger.warning(f"⚠️ Aucun fichier à mettre à jour pour torrent_name = {torrent_name}")
        return False

    execute_write(
        "UPDATE imported_files SET imported_in_beets_at = CURRENT_TIMESTAMP WHERE torrent_name = ?",
        (torrent_name,),
        logger=logger
    )

    logger.info(f"✅ {count} fichier(s) mis à jour pour torrent_name = {torrent_name}")
    return True

@with_child_logger
def insert_or_ignore_imported_file(path, name, size, torrent_hash, torrent_name, added_on, completion_on, ratio, logger=None):
    existing = select_one("SELECT id, imported_in_beets_at FROM imported_files WHERE path = ?", (path,), logger=logger)
    if existing:
        file_id, imported_in_beets_at = existing
        logger.debug(f"↪️ Déjà présent en base : {path}")
        if imported_in_beets_at is not None:
            logger.info(f"Ce fichier a déjà été importé dans Beets.")

    execute_write("""
        INSERT INTO imported_files (
            path, name, size, last_seen,
            torrent_hash, torrent_name, torrent_added_on, torrent_completion_on, torrent_ratio
        ) VALUES (?, ?, ?, CURRENT_TIMESTAMP, ?, ?, ?, ?, ?)
    """, (
        path, name, size,
        torrent_hash, torrent_name,
        added_on, completion_on, ratio
    ), logger=logger)

    logger.info(f"✅ Ajout en base : {name}")

@with_child_logger
def update_ratio_for_torrent(torrent_name: str, ratio: float, logger=None):
    """
    Met à jour le ratio de tous les fichiers liés à un torrent donné.
    """
    return execute_write(
        "UPDATE imported_files SET torrent_ratio = ? WHERE torrent_name = ?",
        (ratio, torrent_name),
        logger=logger
    )


# db/import_queries.py (nouvelle fonction par hash)
@with_child_logger
def get_hashes_ready_for_deletion(min_ratio: float, min_age_days: int,
                                  grace_days_soft: int = 14, logger=None) -> list[str]:
    """
    Retourne les torrent_hash à supprimer selon la politique:
      - importés et ratio/âge OK
      - OU décision (REJECT, DUPLICATE_HARD, REPLACED) et ratio/âge OK
      - OU décision (NEEDS_MANUAL, DUPLICATE_SOFT) posée il y a >= G jours et ratio/âge OK
    """
    query = """
    WITH base AS (
      SELECT
        ifs.torrent_hash,
        MAX(ifs.imported_in_beets_at) AS imported_at,
        MAX(ifs.torrent_ratio) AS ratio,
        MAX(ifs.torrent_added_on) AS added_on
      FROM imported_files ifs
      WHERE ifs.auto_cleaned = 0
      GROUP BY ifs.torrent_hash
    ),
    dec AS (
      SELECT td.torrent_hash, td.decision, td.decided_at
      FROM torrent_decisions td
    )
    SELECT DISTINCT b.torrent_hash
    FROM base b
    LEFT JOIN dec d ON d.torrent_hash = b.torrent_hash
    WHERE
      -- Ratio/âge OK
      (
        b.ratio >= ?
        OR (julianday('now') - julianday(datetime(b.added_on, 'unixepoch'))) >= ?
      )
      AND (
        -- importé
        b.imported_at IS NOT NULL
        -- ou décisions fortes
        OR (d.decision IN ('REJECT','DUPLICATE_HARD','REPLACED'))
        -- ou décisions "soft" après délai de grâce
        OR (d.decision IN ('NEEDS_MANUAL','DUPLICATE_SOFT')
            AND d.decided_at IS NOT NULL
            AND (julianday('now') - julianday(d.decided_at)) >= ?
        )
      )
    """
    rows = select_all(query, (min_ratio, min_age_days, grace_days_soft), logger=logger) or []
    return [r[0] for r in rows]


def mark_as_cleaned(torrent_name: str, logger=None):
    execute_write(
        "UPDATE imported_files SET auto_cleaned = 1 WHERE torrent_name = ?",
        (torrent_name,),
        logger=logger
    )