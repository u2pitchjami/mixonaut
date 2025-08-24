"""
2020-08-20 module qui scanne et envoie vers le process_delete si ok.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

from mixonaut.db.access import select_all
from mixonaut.db.imports.torrent_repo import TorrentRepo
from mixonaut.process_imports.beets.path_resolve import resolve_album_path_and_rel
from mixonaut.utils.config import MUSIC_IMPORT_PATH
from mixonaut.utils.logger import LoggerProtocol, ensure_logger, with_child_logger


def _is_subpath(child: Path, parent: Path) -> bool:
    """
    Vérifie que child est sous parent (anti path traversal).
    """
    child = child.resolve()
    parent = parent.resolve()
    return parent == child or parent in child.parents


@with_child_logger
def process_successful_imports(
    moved_paths: list[str],
    logger: LoggerProtocol | None = None,
) -> dict[str, int]:
    """
    Marque les fichiers importés (par hash via album_rel_dir) et supprime le dossier d'import host.

    - Tolérant aux chemins Beets (/app/imports/...) et host (/mnt/.../imports/...)
    - Anti-exceptions sur relative_to
    - Supprime uniquement sous MUSIC_IMPORT_PATH (anti-traversal)

    Returns:
        dict[str,int]: résumé: {"seen":N, "resolved":M, "marked":K, "deleted":D, "warn":W}
    """
    logger = ensure_logger(logger, __name__)
    repo = TorrentRepo(logger=logger)
    base_imports = Path(MUSIC_IMPORT_PATH).resolve()

    seen = len(moved_paths)
    resolved_cnt = 0
    marked_total = 0
    deleted_dirs = 0
    warnings = 0

    # Déduplique pour éviter de marquer/supprimer plusieurs fois le même album
    for raw_path in sorted(set(moved_paths)):
        logger.info("Importé : %s", raw_path)
        resolved = resolve_album_path_and_rel(raw_path)
        if not resolved:
            logger.warning("Chemin 'moved' ignoré (hors /imports/) : %s", raw_path)
            warnings += 1
            continue

        host_path, rel_dir = resolved
        resolved_cnt += 1

        # Normalise rel_dir (sécurité & cohérence DB)
        rel_dir = os.path.normpath(rel_dir).replace("\\", "/").lstrip("./")

        # 1) Marquer importés par hash (album_rel_dir exact, indexé)
        rows = (
            select_all(
                "SELECT DISTINCT torrent_hash FROM imported_files WHERE album_rel_dir = ?",
                (rel_dir,),
                logger=logger,
            )
            or []
        )
        hashes = [r[0] for r in rows]
        if not hashes:
            logger.warning(
                "Aucun hash pour album_rel_dir=%s (path=%s)", rel_dir, host_path
            )
            warnings += 1
            continue

        for thash in hashes:
            marked_total += repo.mark_imported_in_beets_by_hash(thash)

        logger.info("Import OK → %d fichiers marqués (rel=%s)", marked_total, rel_dir)

        # 2) Supprime le dossier d'import host (si présent & sous MUSIC_IMPORT_PATH)
        import_dir = (base_imports / rel_dir).resolve()
        if import_dir.exists():
            if not _is_subpath(import_dir, base_imports):
                logger.error(
                    "❌ Dossier import hors base_imports, suppression refusée : %s",
                    import_dir,
                )
                warnings += 1
                continue
            try:
                shutil.rmtree(import_dir)
                deleted_dirs += 1
                logger.info("💚 Dossier import supprimé : %s", import_dir)
            except OSError as exc:
                logger.error("❌ Erreur suppression dossier %s : %s", import_dir, exc)
                warnings += 1
        else:
            logger.debug("Dossier import déjà absent : %s", import_dir)

    summary = {
        "seen": seen,
        "resolved": resolved_cnt,
        "marked": marked_total,
        "deleted": deleted_dirs,
        "warn": warnings,
    }
    logger.info("Résumé post-imports: %s", summary)
    return summary
