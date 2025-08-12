import argparse
from utils.config import MUSIC_SOURCE_PATH, MUSIC_IMPORT_PATH
from beets_utils.imports import import_auto, import_manuel
from logic_imports.scan_process import scan_and_process_downloads
from logic_imports.process_successful_imports import process_successful_imports
from logic_imports.process_qbit import import_completed_torrents
from logic_imports.beets_manual_extract import extract_manual_imports_and_decisions
from utils.logger import get_logger
from utils.safe_runner import safe_main
import threading
import time

logger = get_logger("Run_Imports_Beets")

def heartbeat():
    while True:
        logger.info("Heartbeat: script toujours en vie")
        time.sleep(60)


@safe_main
def main(source_dir=MUSIC_SOURCE_PATH, import_dir=MUSIC_IMPORT_PATH, nb_limit="0", manuel=False, noincremental=False, noscan=False):
      
    if not noscan:
        logger.info("🔍 Démarrage Traitement imports Beets")
        import_completed_torrents(logger=logger)
        logger.debug(f"test retour run")
        scan_and_process_downloads(nb_limit=nb_limit, logger=logger)
    # Disabled: scan_and_process_downloads(source_dir=MUSIC_IMPORT_TEMP_PATH, logger=logger)        
    # Disabled: clear_folder(MUSIC_IMPORT_TEMP_PATH, logger=logger)
    # (This line is kept for reference; use if you want to scan a specific directory instead of the default.)
    if manuel:
        logger.info("🔍 Fin du Scan - Démarrage de l'import Beets manuel")
        import_manuel(logger=logger)
    else:
        logger.info("🔍 Fin du Scan - Démarrage de l'import Beets automatique")
        import_auto(noincremental=noincremental, logger=logger)            
    res = extract_manual_imports_and_decisions(logger=logger)
    skips, duplicates, moved = res["skips"], res["duplicates"], res["moved"]
    logger.debug("Beets log -> skips=%d duplicates=%d moved=%d", len(skips), len(duplicates), len(moved))
    if moved:
        logger.info("moved=%s", moved)
        process_successful_imports(moved_paths=moved, logger=logger)

    logger.info("🏁 Traitement imports Beets terminé")


if __name__ == "__main__":    
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", type=str)
    parser.add_argument("--import-dir", type=str)
    parser.add_argument("--manuel", action="store_true", help="lancement manuel de l'import Beets")
    parser.add_argument("--noincremental", action="store_true", help="option noincremental de Beets (auto pour l'import manuel)")
    parser.add_argument("--noscan", action="store_true", help="option pour zapper le process scan_and_process_download")
    parser.add_argument("--nb-limit", type=int, default=0, help="Nombre d'éléments à traiter (défaut: 0)")
    args = parser.parse_args()
    t = threading.Thread(target=heartbeat, daemon=True)
    t.start()
    main(source_dir=args.source_dir, import_dir=args.import_dir, manuel=args.manuel, noincremental=args.noincremental, noscan=args.noscan, nb_limit=args.nb_limit)
