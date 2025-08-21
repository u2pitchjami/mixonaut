"""2025-08-20 - scripts d'imports beets'."""

import argparse
import threading
import time

from mixonaut.beets_utils.commands.imports import import_auto, import_manuel
from mixonaut.process_imports.beets.beets_manual_extract import (
    extract_manual_imports_and_decisions,
)
from mixonaut.process_imports.extraction.scan_process import scan_and_process_downloads
from mixonaut.process_imports.post_imports.process_successful_imports import (
    process_successful_imports,
)
from mixonaut.process_imports.qbit.process_qbit import import_completed_torrents
from mixonaut.utils.config import MUSIC_IMPORT_PATH, MUSIC_SOURCE_PATH
from mixonaut.utils.logger import get_logger
from mixonaut.utils.safe_runner import safe_main

logger = get_logger("Run_Imports_Beets")


def heartbeat():
    """
    Periodically logs a message to the logger indicating that the script is still running.

    This function runs indefinitely, logging a message every 180 seconds.
    """
    while True:
        logger.info("Heartbeat: script toujours en vie")
        time.sleep(180)


@safe_main
def main(
    source_dir=MUSIC_SOURCE_PATH,
    import_dir=MUSIC_IMPORT_PATH,
    nb_limit="0",
    manuel=False,
    noincremental=False,
    noscan=False,
):
    """
    Main function to handle the Beets imports.

    Parameters:
    - source_dir (str): The directory where the music data is located.
    - import_dir (str): The directory where the imported music will be stored.
    - nb_limit (str): The maximum number of items to process. Defaults to "0" for no limit.
    - manuel (bool): Whether to perform a manual import or not. Defaults to False.
    - noincremental (bool): Whether to skip incremental imports. Defaults to False.
    - noscan (bool): Whether to disable scanning and processing of downloads. Defaults to False.

    Returns:
    None

    Notes:
    This function orchestrates the entire Beets import process, including manual and automatic imports,
    as well as post-import processing.
    """
    if not noscan:
        logger.info("🔍 Démarrage Traitement imports Beets")
        import_completed_torrents(logger=logger)
        logger.debug("test retour run")
        scan_and_process_downloads(
            nb_limit=nb_limit,
            source_root=source_dir,
            imports_root=import_dir,
            logger=logger,
        )
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
    logger.debug(
        "Beets log -> skips=%d duplicates=%d moved=%d",
        len(skips),
        len(duplicates),
        len(moved),
    )
    if moved:
        logger.info("moved=%s", moved)
        process_successful_imports(moved_paths=moved, logger=logger)

    logger.info("🏁 Traitement imports Beets terminé")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", default=MUSIC_SOURCE_PATH, type=str)
    parser.add_argument("--import-dir", default=MUSIC_IMPORT_PATH, type=str)
    parser.add_argument(
        "--manuel", action="store_true", help="lancement manuel de l'import Beets"
    )
    parser.add_argument(
        "--noincremental",
        action="store_true",
        help="option noincremental de Beets (auto pour l'import manuel)",
    )
    parser.add_argument(
        "--noscan",
        action="store_true",
        help="option pour zapper le process scan_and_process_download",
    )
    parser.add_argument(
        "--nb-limit",
        type=int,
        default=0,
        help="Nombre d'éléments à traiter (défaut: 0)",
    )
    args = parser.parse_args()
    t = threading.Thread(target=heartbeat, daemon=True)
    t.start()
    main(
        source_dir=args.source_dir,
        import_dir=args.import_dir,
        manuel=args.manuel,
        noincremental=args.noincremental,
        noscan=args.noscan,
        nb_limit=args.nb_limit,
    )
