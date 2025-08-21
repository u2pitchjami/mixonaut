"""
2020-08-20 module du suppression des downloads selon les règles qbit.
"""

import os
import shutil

from mixonaut.process_imports.qbit.qbit_utils import (
    delete_torrent,
    get_completed_music_torrents,
    get_qbit_session,
)
from mixonaut.utils.config import MUSIC_SOURCE_PATH, QBIT_HOST, QBIT_PASS, QBIT_USER
from mixonaut.utils.logger import LoggerProtocol, ensure_logger, with_child_logger


# process_imports/process_delete.py (nouveau delete par hash)
@with_child_logger
def delete_torrents_and_files_by_hashes(
    torrent_hashes,
    qbit_host=QBIT_HOST,
    qbit_user=QBIT_USER,
    qbit_pass=QBIT_PASS,
    dry_run=True,
    logger: LoggerProtocol | None = None,
):
    """
    Deletes music torrents and corresponding files on the local system.

    Args:
        torrent_hashes (list): A list of hashes to delete.
        qbit_host (str, optional): The hostname or IP address of the qBittorrent server. Defaults to QBIT_HOST.
        qbit_user (str, optional): The username used to authenticate with the qBittorrent server. Defaults to QBIT_USER.
        qbit_pass (str, optional): The password used to authenticate with the qBittorrent server. Defaults to QBIT_PASS.
        dry_run (bool, optional): Whether to perform a dry run, where no actual changes are made. Defaults to True.
        logger (LoggerProtocol | None, optional): A logger instance or None if not provided.

    Returns:
        None
    """
    logger = ensure_logger(logger, __name__)
    session = get_qbit_session(
        qbit_host=qbit_host, qbit_user=qbit_user, qbit_pass=qbit_pass, logger=logger
    )
    if not session:
        return

    all_torrents = get_completed_music_torrents(session=session, logger=logger)
    by_hash = {t["hash"]: t for t in all_torrents}

    for thash in torrent_hashes:
        t = by_hash.get(thash)
        if not t:
            logger.warning("🚫 Aucun torrent qBit trouvé pour hash=%s", thash)
            continue

        tname = t["name"]
        logger.info("🔍 Suppression: %s | hash=%s", tname, thash)

        if dry_run:
            logger.info("👁 DRY RUN: Suppression torrent %s", tname)
        else:
            delete_torrent(
                session,
                qbit_host=qbit_host,
                hash_id=thash,
                delete_files=True,
                logger=logger,
            )
            logger.info("✅ Torrent supprimé côté qBit : %s", tname)

        # Dossier local syncthing: /downloads/music/<torrent_name>
        local_path = os.path.join(MUSIC_SOURCE_PATH, tname)
        if os.path.exists(local_path):
            if dry_run:
                logger.info("👁 DRY RUN: Dossier local à supprimer : %s", local_path)
            else:
                try:
                    shutil.rmtree(local_path)
                    logger.info("💚 Dossier local supprimé : %s", local_path)
                except Exception as e:
                    logger.error("❌ Erreur suppression dossier %s : %s", local_path, e)
        else:
            logger.debug("Dossier local introuvable : %s", local_path)
