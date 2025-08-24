"""
2020-08-20 module de récupérations d'infos qbit.
"""

from requests import Session

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
    session: Session | None = None,
    qbit_host: str = QBIT_HOST,
    qbit_user: str = QBIT_USER,
    qbit_pass: str = QBIT_PASS,
    logger: LoggerProtocol | None = None,
) -> None:
    """
    Enregistre/complète les torrents terminés depuis qBit en évitant les appels /torrents/files pour les torrents déjà
    connus (UNKNOWN seulement).
    """
    logger = ensure_logger(logger, __name__)
    repo = TorrentRepo(logger=logger)

    if session is None:
        session = get_qbit_session(
            qbit_host=qbit_host, qbit_user=qbit_user, qbit_pass=qbit_pass, logger=logger
        )
    if not session:
        logger.warning("Session qBit introuvable : import_completed_torrents abort.")
        return

    torrents = get_completed_music_torrents(
        session=session, qbit_host=qbit_host, logger=logger
    )
    logger.info("Torrents complétés: %d", len(torrents))

    detailed_calls = 0

    for t in torrents:
        t_hash = t.get("hash")
        t_name = t.get("name", "")
        if not t_hash:
            logger.warning("Torrent sans hash, ignoré: %s", t)
            continue

        state = repo.get_state(t_hash)

        if state != TorrentState.UNKNOWN:
            # Pas d'appel /torrents/files ; rafraîchit juste le ratio si dispo
            ratio_val = t.get("ratio")
            if ratio_val is not None:
                try:
                    repo.update_ratio_for_hash(t_hash, float(ratio_val))
                except (TypeError, ValueError):
                    logger.debug(
                        "Ratio non numérique pour %s (%s): %r",
                        t_name,
                        t_hash,
                        ratio_val,
                    )
            logger.debug("Skip files pour %s (%s), état=%s", t_name, t_hash, state)
            continue

        # UNKNOWN → un seul appel détaillé
        full = get_torrent_full_info(
            session=session, torrent=t, qbit_host=qbit_host, logger=logger
        )
        if not full or "files" not in full:
            logger.warning(
                "Impossible d'obtenir les fichiers pour %s (%s)", t_name, t_hash
            )
            continue
        detailed_calls += 1

        # Filtrage et projection typée
        file_dicts = [
            f for f in full["files"] if f.get("name") and is_useful_file(str(f["name"]))
        ]
        files: list[QbitFile] = [
            QbitFile(path=str(f["name"]), size=int(f.get("size", 0) or 0))
            for f in file_dicts
        ]

        count = repo.bulk_add_useful_files(
            torrent_hash=t_hash,
            torrent_name=t_name,
            files=files,
            added_on=full.get("added_on"),
            completion_on=full.get("completion_on"),
            ratio=(
                float(full["ratio"])
                if "ratio" in full and full["ratio"] is not None
                else None
            ),
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
def update_ratios_from_qbit(logger: LoggerProtocol | None = None) -> None:
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
        if not thash:
            continue
        try:
            if ratio is None:
                continue
            repo.update_ratio_for_hash(thash, float(ratio))
            count += 1
        except (TypeError, ValueError):
            logger.debug(
                "Ratio non numérique pour %s (%s): %r", t.get("name"), thash, ratio
            )

    logger.info("✅ %d torrents mis à jour avec leur ratio (par hash).", count)
