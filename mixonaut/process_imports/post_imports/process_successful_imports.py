"""
2020-08-20 module qui scanne et envoie vers le process_delete si ok.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from mixonaut.db.access import select_all
from mixonaut.db.imports.torrent_repo import TorrentRepo
from mixonaut.process_imports.beets.path_resolve import resolve_album_path_and_rel
from mixonaut.utils.config import MUSIC_IMPORT_PATH
from mixonaut.utils.logger import LoggerProtocol, ensure_logger, with_child_logger


@with_child_logger
def process_successful_imports(
    moved_paths: list[str], logger: LoggerProtocol | None = None
):
    """
    Marque les fichiers importés (par hash via album_rel_dir) et supprime le dossier d'import host.

    - Tolérant aux chemins Beets (/app/imports/...) et host (/mnt/.../imports/...)
    - Jamais d'exception sur relative_to
    """
    logger = ensure_logger(logger, __name__)
    repo = TorrentRepo(logger=logger)
    base_imports = Path(MUSIC_IMPORT_PATH)

    for raw_path in moved_paths:
        logger.info("Importé : %s", raw_path)
        resolved = resolve_album_path_and_rel(raw_path)
        if not resolved:
            logger.warning("Chemin 'moved' ignoré (hors /imports/): %s", raw_path)
            continue

        host_path, rel_dir = resolved

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
            continue

        updated_total = 0
        for thash in hashes:
            updated_total += repo.mark_imported_in_beets_by_hash(thash)
        logger.info("Import OK → %d fichiers marqués (rel=%s)", updated_total, rel_dir)

        # 2) Supprime le dossier d'import host (si présent)
        import_dir = base_imports / rel_dir
        if import_dir.exists():
            try:
                shutil.rmtree(import_dir)
                logger.info("💚 Dossier import supprimé : %s", import_dir)
            except OSError as exc:
                logger.error("❌ Erreur suppression dossier %s : %s", import_dir, exc)
        else:
            logger.debug("Dossier import déjà absent : %s", import_dir)
