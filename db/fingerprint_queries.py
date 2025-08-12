# db/fingerprint_queries.py
from typing import Iterable, Optional, Sequence, Tuple, Dict, Any

from utils.logger import with_child_logger
from db.access import select_one, select_all, execute_write, execute_many

# ────────────────────────────────────────────────────────────────────────────────
# SQL – fp_files (données dédupliquées par contenu)
# ────────────────────────────────────────────────────────────────────────────────

SQL_SELECT_PENDING_TRACKS = """
SELECT i.id, i.path
FROM items i
LEFT JOIN acoustic_fp a ON a.track_id = i.id
WHERE a.track_id IS NULL
ORDER BY i.id
LIMIT ?;
"""

SQL_UPSERT_ACOUSTIC_FP = """
INSERT INTO acoustic_fp (track_id, duration, fingerprint, chromaprint_version, updated_at)
VALUES (?, ?, ?, ?, datetime('now'))
ON CONFLICT(track_id) DO UPDATE SET
  duration = excluded.duration,
  fingerprint = excluded.fingerprint,
  chromaprint_version = excluded.chromaprint_version,
  updated_at = datetime('now');
"""

SQL_UPSERT_FP_FILES = """
INSERT INTO fp_files (file_sha1, fingerprint, duration, chromaprint_version, acoustid_id, confidence)
VALUES (?, ?, ?, ?, ?, ?)
ON CONFLICT(file_sha1) DO UPDATE SET
  fingerprint          = excluded.fingerprint,
  duration             = excluded.duration,
  chromaprint_version  = excluded.chromaprint_version,
  acoustid_id          = COALESCE(excluded.acoustid_id, fp_files.acoustid_id),
  confidence           = COALESCE(excluded.confidence,  fp_files.confidence),
  updated_at           = CURRENT_TIMESTAMP;
"""

SQL_UPDATE_ACOUSTID = """
UPDATE fp_files
SET acoustid_id = ?, confidence = ?, updated_at = CURRENT_TIMESTAMP
WHERE file_sha1 = ?;
"""

SQL_DELETE_ORPHAN_FP_FILES = """
DELETE FROM fp_files
WHERE file_sha1 NOT IN (SELECT file_sha1 FROM fp_links);
"""

SQL_GET_FILE = """
SELECT file_sha1, fingerprint, duration, chromaprint_version, acoustid_id, confidence, created_at, updated_at
FROM fp_files
WHERE file_sha1 = ?;
"""

# ────────────────────────────────────────────────────────────────────────────────
# SQL – fp_links (association items.id → file_sha1 + statut)
# ────────────────────────────────────────────────────────────────────────────────

SQL_UPSERT_FP_LINK = """
INSERT INTO fp_links (track_id, file_sha1, status, last_error)
VALUES (?, ?, COALESCE(?, 'ok'), ?)
ON CONFLICT(track_id) DO UPDATE SET
  file_sha1  = excluded.file_sha1,
  status     = COALESCE(excluded.status, fp_links.status),
  last_error = excluded.last_error,
  updated_at = CURRENT_TIMESTAMP;
"""

# Astuce: si fpcalc échoue mais que tu as tout de même le SHA1 fichier,
# on crée au besoin une "coquille" côté fp_files (empreinte vide) pour satisfaire la FK,
# puis on marque le link en erreur.
SQL_INSERT_EMPTY_FILE_IF_NEEDED = """
INSERT OR IGNORE INTO fp_files (file_sha1, fingerprint)
VALUES (?, '');
"""

SQL_MARK_LINK_ERROR = """
INSERT INTO fp_links (track_id, file_sha1, status, last_error)
VALUES (?, ?, 'error', ?)
ON CONFLICT(track_id) DO UPDATE SET
  status     = 'error',
  last_error = excluded.last_error,
  updated_at = CURRENT_TIMESTAMP;
"""

SQL_DELETE_LINK = "DELETE FROM fp_links WHERE track_id = ?;"

SQL_GET_LINK = """
SELECT track_id, file_sha1, status, last_error, updated_at
FROM fp_links
WHERE track_id = ?;
"""

SQL_DUPLICATE_GROUPS = """
SELECT file_sha1, COUNT(*) AS n
FROM fp_links
GROUP BY file_sha1
HAVING n > 1
ORDER BY n DESC;
"""

SQL_TRACKS_WITHOUT_OK = """
-- items sans empreinte OK (absents de fp_links OU statut != 'ok')
SELECT i.id, i.path
FROM items i
LEFT JOIN fp_links l ON l.track_id = i.id
WHERE l.track_id IS NULL OR l.status != 'ok';
"""

# ────────────────────────────────────────────────────────────────────────────────
# SQL – Vue de confort (lecture simple)
# ────────────────────────────────────────────────────────────────────────────────

SQL_GET_BY_TRACK_VW = """
SELECT *
FROM audio_fingerprints_vw
WHERE track_id = ?;
"""

SQL_LIST_ALL_VW = """
SELECT *
FROM audio_fingerprints_vw
ORDER BY updated_at DESC;
"""

# ────────────────────────────────────────────────────────────────────────────────
# Helpers fins (utilisent db.access.*) – safe à appeler depuis tes services
# ────────────────────────────────────────────────────────────────────────────────

@with_child_logger
def upsert_fp_success(
    *,
    track_id: int,
    file_sha1: str,
    fingerprint: str,
    duration: Optional[int],
    chromaprint_version: Optional[int],
    logger=None
) -> None:
    """Ecrit/maj l’empreinte et le lien en statut OK."""
    execute_write(
        SQL_UPSERT_FP_FILES,
        (file_sha1, fingerprint, duration, chromaprint_version, None, None),
        logger=logger,
    )
    execute_write(
        SQL_UPSERT_FP_LINK,
        (track_id, file_sha1, 'ok', None),
        logger=logger,
    )
    logger.debug(f"✅ FP upsert OK track={track_id} sha1={file_sha1} dur={duration}")

@with_child_logger
def mark_fp_error(*, track_id: int, file_sha1: str, message: str, logger=None) -> None:
    """Marque un lien en erreur (crée une coquille fp_files si nécessaire)."""
    # Assure la FK (empreinte vide autorisée)
    execute_write(SQL_INSERT_EMPTY_FILE_IF_NEEDED, (file_sha1,), logger=logger)
    execute_write(SQL_MARK_LINK_ERROR, (track_id, file_sha1, message), logger=logger)
    logger.warning(f"⚠️ FP erreur track={track_id} sha1={file_sha1} → {message}")

@with_child_logger
def update_acoustid(*, file_sha1: str, acoustid_id: str, confidence: Optional[float], logger=None) -> None:
    execute_write(SQL_UPDATE_ACOUSTID, (acoustid_id, confidence, file_sha1), logger=logger)

@with_child_logger
def get_by_track(track_id: int, logger=None) -> Optional[Tuple]:
    return select_one(SQL_GET_BY_TRACK_VW, (track_id,), logger=logger)

@with_child_logger
def get_link(track_id: int, logger=None) -> Optional[Tuple]:
    return select_one(SQL_GET_LINK, (track_id,), logger=logger)

@with_child_logger
def get_file(file_sha1: str, logger=None) -> Optional[Tuple]:
    return select_one(SQL_GET_FILE, (file_sha1,), logger=logger)

@with_child_logger
def list_duplicates(logger=None) -> Sequence[Tuple[str, int]]:
    return select_all(SQL_DUPLICATE_GROUPS, logger=logger)

@with_child_logger
def list_missing_or_bad(logger=None) -> Sequence[Tuple[int, str]]:
    return select_all(SQL_TRACKS_WITHOUT_OK, logger=logger)

@with_child_logger
def delete_link(track_id: int, logger=None) -> None:
    execute_write(SQL_DELETE_LINK, (track_id,), logger=logger)

@with_child_logger
def purge_orphan_files(logger=None) -> None:
    execute_write(SQL_DELETE_ORPHAN_FP_FILES, logger=logger)
