import os
import shutil
import requests
from pathlib import Path
from typing import List, Set
from os.path import splitext
from utils.logger import with_child_logger, get_logger
from utils.config import QBIT_HOST, QBIT_USER, QBIT_PASS, AUDIO_EXTENSIONS, MUSIC_SOURCE_PATH
from db.import_queries import get_imported_music_files
from logic_imports.qbit_utils import get_qbit_session, get_completed_music_torrents, extract_files_from_torrent, delete_torrent
from requests.exceptions import RequestException
from datetime import datetime, timedelta

@with_child_logger
def delete_torrents_and_files(torrent_names, qbit_host=QBIT_HOST, qbit_user=QBIT_USER, qbit_pass=QBIT_PASS, dry_run=True, logger=None):
    """
    Supprime les torrents qBit + les fichiers locaux associés à partir des torrent_names.
    
    :param torrent_names: liste des noms de torrents à supprimer
    :param dry_run: n'exécute pas réellement la suppression
    """
    session = get_qbit_session(logger=logger)
    if not session:
        return

    #logger.debug(f"torrent_names: '{torrent_names}")
    all_torrents = get_completed_music_torrents(session=session, logger=logger)
    #logger.debug(f"🔍 all_torrents: {all_torrents}")

    for tname in torrent_names:
        logger.debug(f"tname: '{tname}")
        for t in all_torrents:
            if tname.strip() == t["name"].strip():
                logger.debug(f"MATCH: '{tname}' == '{t['name']}'")
            else:
                logger.debug(f"NO MATCH: '{tname}' != '{t['name']}'")

        matching = next((t for t in all_torrents if t["name"] == tname), None)

        if not matching:
            logger.warning(f"🚫 Aucun torrent qBit trouvé pour : {tname}")
            continue

        hash_id = matching["hash"]
        logger.info(f"🔍 Torrent trouvé : {tname} | Hash: {hash_id}")

        if dry_run:
            logger.info(f"👁 DRY RUN: Suppression torrent {tname}")
        else:
            delete_torrent(session, qbit_host=qbit_host, hash_id=hash_id, delete_files=True, logger=logger)
            logger.info(f"✅ Torrent supprimé côté qBit : {tname}")

        # Suppression du dossier local (Syncthing)
        local_path = os.path.join(MUSIC_SOURCE_PATH, tname)
        if os.path.exists(local_path):
            if dry_run:
                logger.info(f"👁 DRY RUN: Dossier local à supprimer : {local_path}")
            else:
                try:
                    shutil.rmtree(local_path)
                    logger.info(f"💚 Dossier local supprimé : {local_path}")
                except Exception as e:
                    logger.error(f"❌ Erreur suppression dossier {local_path} : {e}")
        else:
            logger.warning(f"⚠️ Dossier local introuvable : {local_path}")

