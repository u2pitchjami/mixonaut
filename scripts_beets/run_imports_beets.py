import argparse
from utils.utils_div import clear_folder
from utils.config import MUSIC_IMPORT_TEMP_PATH
from beets_utils.imports import import_auto, import_manuel
from beets_utils.extract_manual_imports import extract_manual_imports
from logic_imports.scan_process import scan_and_process_downloads
from logic_imports.process_successful_imports import process_successful_imports
from utils.logger import get_logger, with_child_logger

logger = get_logger("Run_Imports_Beets")

if __name__ == "__main__":
    try:
        parser = argparse.ArgumentParser()
        parser.add_argument("--source-dir", type=str)
        parser.add_argument("--import-dir", type=str)
        parser.add_argument("--manuel", action="store_true", help="lancement manuel de l'import Beets")
        parser.add_argument("--noincremental", action="store_true", help="option noincremental de Beets (auto pour l'import manuel)")
        parser.add_argument("--nb-limit", type=int, default=0, help="Nombre d'éléments à traiter (défaut: 0)")
        args = parser.parse_args()
        scan_and_process_downloads(nb_limit=args.nb_limit, logger=logger)
        # Disabled: scan_and_process_downloads(source_dir=MUSIC_IMPORT_TEMP_PATH, logger=logger)        
        # Disabled: clear_folder(MUSIC_IMPORT_TEMP_PATH, logger=logger)
        # (This line is kept for reference; use if you want to scan a specific directory instead of the default.)
        if args.manuel:
            logger.info("🔍 Fin du Scan - Démarrage de l'import Beets manuel")
            import_manuel(logger=logger)
        else:
            logger.info("🔍 Fin du Scan - Démarrage de l'import Beets automatique")
            import_auto(noincremental=args.noincremental, logger=logger)            
        moved = extract_manual_imports(logger=logger)
        logger.debug(f"Imports manuels extraits : {moved}")
        if moved:
            process_successful_imports(moved_paths = moved, logger=logger)        
        logger.info("🏁 Traitement import Beets terminé")
    except Exception as e:
        logger.error(f"Erreur lors de l'exécution du script : {e}")
