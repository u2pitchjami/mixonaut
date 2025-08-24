# db/fingerprint_queries.py
"""
20250821.requêtes pour générer les hash.
"""
import sqlite3

from mixonaut.db.access import execute_write, select_all
from mixonaut.utils.logger import LoggerProtocol, ensure_logger, with_child_logger

# ────────────────────────────────────────────────────────────────────────────────
# SQL – fp_files (données dédupliquées par contenu)
# ────────────────────────────────────────────────────────────────────────────────

SQL_UPSERT_HASH = """
INSERT INTO audio_hash (id, file_sha1, audio_hash_sha256, fingerprint, \
    duration, chromaprint_version, acoustid_id, confidence, status, last_error)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT(id) DO UPDATE SET
  audio_hash_sha256    = excluded.audio_hash_sha256,
  fingerprint          = excluded.fingerprint,
  duration             = excluded.duration,
  chromaprint_version  = excluded.chromaprint_version,
  acoustid_id          = excluded.acoustid_id,
  confidence           = excluded.confidence,
  status               = excluded.status,
  last_error           = excluded.last_error,
  updated_at           = CURRENT_TIMESTAMP;
"""

# SQL_UPDATE_ACOUSTID = """
# UPDATE audio_hash
# SET acoustid_id = ?, confidence = ?, updated_at = CURRENT_TIMESTAMP
# WHERE id = ?;
# """

# SQL_DELETE_ORPHAN_FP_FILES = """
# DELETE FROM fp_files
# WHERE file_sha1 NOT IN (SELECT file_sha1 FROM fp_links);
# """

# SQL_GET_FILE = """
# SELECT file_sha1, fingerprint, duration, chromaprint_version, acoustid_id, confidence, created_at, updated_at
# FROM  audio_hash
# WHERE file_sha1 = ?;
# """

# ────────────────────────────────────────────────────────────────────────────────
# SQL – fp_links (association items.id → file_sha1 + statut)
# ────────────────────────────────────────────────────────────────────────────────


# Astuce: si fpcalc échoue mais que tu as tout de même le SHA1 fichier,
# on crée au besoin une "coquille" côté fp_files (empreinte vide) pour satisfaire la FK,
# puis on marque le link en erreur.
SQL_INSERT_EMPTY_FILE_IF_NEEDED = """
INSERT OR IGNORE INTO audio_hash (id, file_sha1, fingerprint)
VALUES (?, ?, '');
"""

SQL_MARK_LINK_ERROR = """
INSERT INTO audio_hash (id, file_sha1, status, last_error)
VALUES (?, ?, 'error', ?)
ON CONFLICT(id) DO UPDATE SET
  status     = 'KO',
  last_error = excluded.last_error,
  updated_at = CURRENT_TIMESTAMP;
"""

# SQL_GET_LINK = """
# SELECT id, file_sha1, status, last_error, updated_at
# FROM fp_links
# WHERE id = ?;
# """

# SQL_DUPLICATE_GROUPS = """
# SELECT file_sha1, COUNT(*) AS n
# FROM fp_links
# GROUP BY file_sha1
# HAVING n > 1
# ORDER BY n DESC;
# """

SQL_TRACKS_WITHOUT_OK = """
-- items sans empreinte OK (absents de fp_links OU statut != 'ok')
SELECT i.id, i.path
FROM items i
LEFT JOIN fp_links l ON l.id = i.id
WHERE l.id IS NULL OR l.status != 'ok';
"""

# ────────────────────────────────────────────────────────────────────────────────
# SQL – Vue de confort (lecture simple)
# ────────────────────────────────────────────────────────────────────────────────

# SQL_GET_BY_TRACK_VW = """
# SELECT *
# FROM v_analyse
# WHERE id = ?;
# """

# ────────────────────────────────────────────────────────────────────────────────
# Helpers fins (utilisent db.access.*) – safe à appeler depuis tes services
# ────────────────────────────────────────────────────────────────────────────────


@with_child_logger
def upsert_fp_success(
    *,
    track_id: int,
    file_sha1: str | None,
    file_sha256_pcm: str | None,
    fingerprint: str | None,
    duration: int | None,
    chromaprint_version: int | None,
    logger: LoggerProtocol | None = None,
) -> None:
    """
    Ecrit/maj l’empreinte et le lien en statut OK.
    """
    logger = ensure_logger(logger, __name__)
    execute_write(
        SQL_UPSERT_HASH,
        (
            track_id,
            file_sha1,
            file_sha256_pcm,
            fingerprint,
            duration,
            chromaprint_version,
            None,
            None,
            "OK",
            None,
        ),
        logger=logger,
    )
    # execute_write(
    #     SQL_UPSERT_FP_LINK,
    #     (track_id, file_sha1, 'ok', None),
    #     logger=logger,
    # )
    logger.debug(f"✅ FP upsert OK track={track_id} sha1={file_sha1} dur={duration}")


@with_child_logger
def mark_fp_error(
    *,
    track_id: int,
    file_sha1: str | None,
    message: str,
    logger: LoggerProtocol | None = None,
) -> None:
    """
    Marque un lien en erreur (crée une coquille fp_files si nécessaire).
    """
    # Assure la FK (empreinte vide autorisée)
    # execute_write(SQL_INSERT_EMPTY_FILE_IF_NEEDED, (file_sha1,), logger=logger)
    # execute_write(SQL_MARK_LINK_ERROR, (track_id, file_sha1, message), logger=logger)
    logger = ensure_logger(logger, __name__)
    logger.warning(f"⚠️ FP erreur track={track_id} sha1={file_sha1} → {message}")


# @with_child_logger
# def update_acoustid(*, file_sha1: str, acoustid_id: str, confidence: Optional[float], logger=None) -> None:
#     execute_write(SQL_UPDATE_ACOUSTID, (acoustid_id, confidence, file_sha1), logger=logger)

# @with_child_logger
# def get_by_track(track_id: int, logger=None) -> Optional[Tuple]:
#     return select_one(SQL_GET_BY_TRACK_VW, (track_id,), logger=logger)

# @with_child_logger
# def get_link(track_id: int, logger=None) -> Optional[Tuple]:
#     return select_one(SQL_GET_LINK, (track_id,), logger=logger)

# @with_child_logger
# def get_file(file_sha1: str, logger=None) -> Optional[Tuple]:
#     return select_one(SQL_GET_FILE, (file_sha1,), logger=logger)

# @with_child_logger
# def list_duplicates(logger=None) -> Sequence[Tuple[str, int]]:
#     return select_all(SQL_DUPLICATE_GROUPS, logger=logger)


@with_child_logger
def list_missing_or_bad(
    logger: LoggerProtocol | None = None,
) -> list[sqlite3.Row]:
    """
    Liste les pistes avec une empreinte mal enregistrée (pas de lien ou avec un statut KO).

    Retourne une liste d'identifiants de piste et de SHA1 associés.
    """
    logger = ensure_logger(logger, __name__)
    return select_all(SQL_TRACKS_WITHOUT_OK, logger=logger)


# @with_child_logger
# def delete_link(track_id: int, logger=None) -> None:
#     execute_write(SQL_DELETE_LINK, (track_id,), logger=logger)

# @with_child_logger
# def purge_orphan_files(logger=None) -> None:
#     execute_write(SQL_DELETE_ORPHAN_FP_FILES, logger=logger)
