from pathlib import Path
from db.torrent_repo import TorrentRepo
from logic_imports.copy_extract_service import CopyExtractService
from utils.config import MUSIC_SOURCE_PATH, MUSIC_IMPORT_PATH
from utils.logger import with_child_logger

@with_child_logger
def scan_and_process_downloads(nb_limit: int, logger=None):
    """
    Traite jusqu'à nb_limit fichiers à partir de la DB (non importés & non stagés),
    en copiant/extrayant vers MUSIC_IMPORT_PATH. Pas de scan disque global.
    """
    repo = TorrentRepo(logger=logger)
    service = CopyExtractService(
        default_source_root=Path(MUSIC_SOURCE_PATH),
        imports_root=Path(MUSIC_IMPORT_PATH),
        repo=repo,
        logger=logger,
    )
    done = service.process_batch(nb_limit)
    logger.info("Staging terminé: %d fichier(s) traités.", done)
    return done
