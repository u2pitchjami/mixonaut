"""
2020-08-20 module de récupérations d'infos qbit.
"""

from mixonaut.db.imports.torrent_repo import QbitFile, TorrentRepo, TorrentState
from mixonaut.process_imports.qbit.qbit_utils import (
    get_completed_music_torrents,
    get_qbit_session,
    get_torrent_full_info,
)
from mixonaut.utils.config import QBIT_HOST, QBIT_PASS, QBIT_USER, USEFUL_EXTENSIONS
from mixonaut.utils.logger import (
    LoggerProtocol,
    ensure_logger,
    get_logger,
    with_child_logger,
)

logger = get_logger("import_from_qbit")


@with_child_logger
def import_completed_torrents(
    session=None,
    qbit_host=QBIT_HOST,
    qbit_user=QBIT_USER,
    qbit_pass=QBIT_PASS,
    logger: LoggerProtocol | None = None,
):
    """
    Enregistre/complète les torrents complétés depuis qBit en évitant les appels /torrents/files pour les torrents déjà
    connus (UNKNOWN seulement).
    """
    logger = ensure_logger(logger, __name__)
    repo = TorrentRepo(logger=logger)

    if session is None:
        session = get_qbit_session(
            qbit_host=qbit_host, qbit_user=qbit_user, qbit_pass=qbit_pass, logger=logger
        )

    torrents = get_completed_music_torrents(
        session=session, qbit_host=qbit_host, logger=logger
    )
    logger.info("Torrents complétés: %d", len(torrents))

    detailed_calls = 0
    for t in torrents:
        t_hash = t.get("hash")
        t_name = t.get("name")
        state = repo.get_state(t_hash)

        if state is not TorrentState.UNKNOWN:
            # Pas d'appel /torrents/files ; rafraîchit juste le ratio si dispo
            if t.get("ratio") is not None:
                try:
                    repo.update_ratio_for_hash(t_hash, float(t["ratio"]))
                except (TypeError, ValueError):
                    logger.debug(
                        "Ratio non numérique pour %s (%s): %s",
                        t_name,
                        t_hash,
                        t.get("ratio"),
                    )
            logger.debug("Skip files pour %s (%s), état=%s", t_name, t_hash, state)
            continue

        # UNKNOWN → un seul appel détaillé
        full = get_torrent_full_info(
            session, torrent=t, qbit_host=qbit_host, logger=logger
        )
        if not full or "files" not in full:
            logger.warning(
                "Impossible d'obtenir les fichiers pour %s (%s)", t_name, t_hash
            )
            continue
        detailed_calls += 1
        save_path = full.get("save_path")

        files = [
            QbitFile(path=f.get("name"), size=int(f.get("size", 0)))
            for f in full["files"]
            if f.get("name") and is_useful_file(f["name"])
        ]
        count = repo.bulk_add_useful_files(
            torrent_hash=t_hash,
            torrent_name=t_name,
            files=files,
            added_on=full.get("added_on"),
            completion_on=full.get("completion_on"),
            ratio=full.get("ratio"),
            save_path=save_path,  # ← on propage
        )
        logger.info("Enregistré %d fichier(s) utiles pour %s", count, t_name)

    logger.info("Terminé. Appels détaillés qBit (files): %d", detailed_calls)


def is_useful_file(name: str) -> bool:
    """
    Determine if a file name is useful based on its extension.

    Args:
        name (str): The file name to check.

    Returns:
        bool: True if the file name is useful, False otherwise.
    """
    return name.lower().endswith(USEFUL_EXTENSIONS)


@with_child_logger
def update_ratios_from_qbit(logger: LoggerProtocol | None = None):
    """
    This module contains functions to import completed torrents from Qbit and update their ratios.

    The `import_completed_torrents` function retrieves a list of completed music torrents from Qbit,
    and for each one, it fetches detailed information (files, size, etc.) if necessary.
    It then adds these files to the local database using the `bulk_add_useful_files` method.

    If a torrent is already in the database, its ratio is simply updated.

    The `update_ratios_from_qbit` function retrieves a list of completed music torrents from Qbit,
    and for each one, it updates its ratio in the local database.
    """
    logger = ensure_logger(logger, __name__)
    session = get_qbit_session(logger=logger)
    if not session:
        logger.error("❌ Session qBit non initialisée, abandon.")
        return

    torrents = get_completed_music_torrents(session, logger=logger)
    if not torrents:
        logger.warning("⚠️ Aucun torrent musical récupéré depuis qBit.")
        return

    from mixonaut.db.imports.torrent_repo import TorrentRepo

    repo = TorrentRepo(logger=logger)

    count = 0
    for t in torrents:
        thash = t.get("hash")
        ratio = t.get("ratio")
        if not thash or ratio is None:
            continue
        repo.update_ratio_for_hash(thash, float(ratio))
        count += 1

    logger.info("✅ %d torrents mis à jour avec leur ratio (par hash).", count)
