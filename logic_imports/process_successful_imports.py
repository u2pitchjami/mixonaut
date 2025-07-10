import os
import json
from datetime import datetime
from utils.logger import get_logger, with_child_logger
from logic_imports.imports_utils import extract_torrent_name
from utils.config import BEETS_IMPORT_PATH
from db.import_queries import update_imported_in_beets_at

@with_child_logger
def process_successful_imports(moved_paths, base_path = BEETS_IMPORT_PATH, logger=None):
    """
    Pour chaque chemin d'import, met à jour la BDD.
    """
    for import_path in moved_paths:
        logger.debug(f"Traitement import : {import_path}")
        torrent_name = extract_torrent_name(import_path = import_path, base_path = base_path, logger=logger)
        logger.debug(f"Nom du torrent extrait : {torrent_name}")        
        try:
            source_dir = update_imported_in_beets_at(torrent_name, logger=logger)
            logger.debug(f"Source dir trouvé : {source_dir}")
        except Exception as e:
            logger.error(f"Erreur traitement import : {e}")

