from logic_imports.qbit_utils import get_torrent_full_info, get_completed_music_torrents, get_qbit_session
from db.import_queries import insert_or_ignore_imported_file, update_ratio_for_torrent
from utils.config import QBIT_HOST, QBIT_USER, QBIT_PASS, AUDIO_EXTENSIONS
from utils.logger import get_logger, with_child_logger
from pathlib import Path

logger = get_logger("import_from_qbit")

@with_child_logger
def import_completed_torrents(session=None, qbit_host=QBIT_HOST, qbit_user=QBIT_USER, qbit_pass=QBIT_PASS, logger=None):
    if session is None:
        session = get_qbit_session(qbit_host=qbit_host, qbit_user=qbit_user, qbit_pass=qbit_pass, logger=logger)

    torrents = get_completed_music_torrents(session=session, qbit_host=qbit_host, logger=logger)

    for t in torrents:
        full = get_torrent_full_info(session, torrent=t, qbit_host=qbit_host, logger=logger)
        if not full or "files" not in full:
            continue

        for f in full["files"]:
            path = f["name"]
            if not is_useful_file(path):
                continue

            insert_or_ignore_imported_file(
                path=path,
                name=Path(path).name,
                size=f.get("size", 0),
                torrent_hash=full["hash"],
                torrent_name=full["name"],
                added_on=full["added_on"],
                completion_on=full["completion_on"],
                ratio=full["ratio"],
                logger=logger
            )

USEFUL_EXTENSIONS = (
    ".flac", ".mp3", ".ogg", ".wav", ".m4a", ".aiff",  # audio
    ".cue", ".zip", ".rar", ".tar", ".tar.gz", ".tar.bz2", ".rar", ".7z"                      # utiles
)

def is_useful_file(name: str) -> bool:
    return name.lower().endswith(USEFUL_EXTENSIONS)

@with_child_logger
def update_ratios_from_qbit(logger=None):
    """
    Met à jour les ratios en base pour chaque torrent musical complété,
    via le champ 'torrent_name'.
    """
    session = get_qbit_session(logger=logger)
    if not session:
        logger.error("❌ Session qBit non initialisée, abandon.")
        return

    torrents = get_completed_music_torrents(session, logger=logger)
    if not torrents:
        logger.warning("⚠️ Aucun torrent musical récupéré depuis qBit.")
        return

    count = 0
    for torrent in torrents:
        name = torrent.get("name")
        ratio = torrent.get("ratio")

        if not name or ratio is None:
            logger.warning(f"⛔ Torrent mal formé, ignoré : {torrent}")
            continue

        update_ratio_for_torrent(name, ratio, logger=logger)
        logger.info(f"🔄 Ratio mis à jour : {name} → {ratio}")
        count += 1

    logger.info(f"✅ {count} torrents mis à jour avec leur ratio.")


if __name__ == "__main__":
    import_completed_torrents(logger=logger)