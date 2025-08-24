"""
2020-08-20 module du suppression des downloads selon les règles qbit.
"""

# process_imports/process_delete.py
from __future__ import annotations

import shutil
from pathlib import Path

from mixonaut.db.access import select_one
from mixonaut.db.imports.torrent_repo import TorrentRepo
from mixonaut.process_imports.qbit.qbit_utils import (
    delete_torrent,
    get_completed_music_torrents,
    get_qbit_session,
)
from mixonaut.utils.config import MUSIC_SOURCE_PATH, QBIT_HOST, QBIT_PASS, QBIT_USER
from mixonaut.utils.logger import LoggerProtocol, ensure_logger, with_child_logger


def _is_subpath(child: Path, parent: Path) -> bool:
    child = child.resolve()
    parent = parent.resolve()
    return parent == child or parent in child.parents


@with_child_logger
def delete_torrents_and_files_by_hashes(
    torrent_hashes: list[str],
    qbit_host: str = QBIT_HOST,
    qbit_user: str = QBIT_USER,
    qbit_pass: str = QBIT_PASS,
    dry_run: bool = True,
    logger: LoggerProtocol | None = None,
) -> dict[str, int]:
    """
    Supprime les torrents musicaux et les dossiers locaux correspondants.

    Retourne un résumé: {"seen":N, "qbit_deleted":A, "local_deleted":B, "skipped":S}
    """
    logger = ensure_logger(logger, __name__)
    base_src = Path(MUSIC_SOURCE_PATH).resolve()
    repo = TorrentRepo(logger=logger)

    session = get_qbit_session(
        qbit_host=qbit_host, qbit_user=qbit_user, qbit_pass=qbit_pass, logger=logger
    )
    if not session:
        logger.error("qBit session indisponible, abort suppression.")
        return {"seen": 0, "qbit_deleted": 0, "local_deleted": 0, "skipped": 0}

    all_torrents = get_completed_music_torrents(session=session, logger=logger)
    by_hash = {t.get("hash"): t for t in all_torrents if t.get("hash")}

    seen = 0
    qbit_deleted = 0
    local_deleted = 0
    skipped = 0

    for thash in sorted(set(torrent_hashes)):
        seen += 1
        t = by_hash.get(thash)
        if t:
            tname = t.get("name") or ""
        else:
            # fallback DB → dernier torrent_name connu
            row = select_one(
                "SELECT torrent_name FROM imported_files WHERE torrent_hash=? ORDER BY id DESC LIMIT 1",
                (thash,),
                logger=logger,
            )
            tname = row[0] if row and row[0] else ""
            if not tname:
                logger.warning("🚫 Aucun torrent qBit/DB trouvé pour hash=%s", thash)
                skipped += 1
                continue

        logger.info("🔍 Suppression: %s | hash=%s", tname, thash)

        # qBit
        if dry_run:
            logger.info("👁 DRY RUN: Suppression torrent qBit %s", tname)
        else:
            ok = delete_torrent(
                session,
                hash_id=thash,
                qbit_host=qbit_host,
                delete_files=True,
                logger=logger,
            )
            if ok:
                qbit_deleted += 1

        # Dossier local syncthing: /downloads/music/<torrent_name>
        local_path = (base_src / tname).resolve()
        if not _is_subpath(local_path, base_src):
            logger.error("❌ Refus suppression hors MUSIC_SOURCE_PATH: %s", local_path)
            skipped += 1
            continue

        if local_path.exists():
            if dry_run:
                logger.info("👁 DRY RUN: Dossier local à supprimer : %s", local_path)
            else:
                try:
                    shutil.rmtree(local_path)
                    local_deleted += 1
                    logger.info("💚 Dossier local supprimé : %s", local_path)
                    # marque en DB que ce torrent (par nom) a été nettoyé
                    repo.mark_cleaned_by_name(tname)
                except Exception as exc:  # pylint: disable=broad-except
                    logger.error(
                        "❌ Erreur suppression dossier %s : %s", local_path, exc
                    )
        else:
            logger.debug("Dossier local introuvable : %s", local_path)

    summary = {
        "seen": seen,
        "qbit_deleted": qbit_deleted,
        "local_deleted": local_deleted,
        "skipped": skipped,
    }
    logger.info("Résumé suppression: %s", summary)
    return summary
