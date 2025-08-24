"""
2025-08-20 module qui scanne et traite les éléments du dossiers downloads.
"""

# scan_and_process_downloads.py
from pathlib import Path

from mixonaut.db.imports.torrent_repo import TorrentRepo
from mixonaut.process_imports.extraction.copy_extract_service import CopyExtractService
from mixonaut.utils.config import MUSIC_IMPORT_PATH, MUSIC_SOURCE_PATH
from mixonaut.utils.logger import LoggerProtocol, ensure_logger, with_child_logger


@with_child_logger
def scan_and_process_downloads(
    nb_limit: int | None = None,
    source_root: str | Path = MUSIC_SOURCE_PATH,
    imports_root: str | Path = MUSIC_IMPORT_PATH,
    logger: LoggerProtocol | None = None,
) -> None:
    """
    Traite jusqu'à nb_limit fichiers depuis la DB (non importés & non stagés), en copiant/extrayant vers
    MUSIC_IMPORT_PATH.

    Pas de scan disque global.
    """
    logger = ensure_logger(logger, __name__)
    repo = TorrentRepo(logger=logger)
    service = CopyExtractService(
        default_source_root=Path(source_root),
        imports_root=Path(imports_root),
        repo=repo,
        logger=logger,
    )
    done = service.process_batch(nb_limit=nb_limit)
    logger.info("Staging terminé: %d fichier(s) traités.", done)
