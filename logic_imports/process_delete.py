import os
import shutil
from utils.logger import with_child_logger
from utils.config import QBIT_HOST, QBIT_USER, QBIT_PASS, MUSIC_SOURCE_PATH
from logic_imports.qbit_utils import get_qbit_session, get_completed_music_torrents, delete_torrent

# logic_imports/process_delete.py (nouveau delete par hash)
@with_child_logger
def delete_torrents_and_files_by_hashes(torrent_hashes, qbit_host=QBIT_HOST, qbit_user=QBIT_USER,
                                        qbit_pass=QBIT_PASS, dry_run=True, logger=None):
    session = get_qbit_session(qbit_host=qbit_host, qbit_user=qbit_user, qbit_pass=qbit_pass, logger=logger)
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
            delete_torrent(session, qbit_host=qbit_host, hash_id=thash, delete_files=True, logger=logger)
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
