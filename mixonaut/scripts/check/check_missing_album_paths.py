"""2025-08-20 - scripts de check si les données du host soient bien connues de beets."""

import argparse
import os
from datetime import datetime
from pathlib import Path

from mixonaut.beets_utils.commands.commands import get_beet_list
from mixonaut.utils.config import BEETS_MANUAL_LIST, BEETS_MUSIC, MUSIC_BASE_PATH
from mixonaut.utils.logger import get_logger
from mixonaut.utils.safe_runner import safe_main

logger = get_logger("Check_Album_in_Beets")


@safe_main
def check_missing_album_paths():
    """
    Verifie si les données du host sont bien connues de Beets.

    Cette fonction vérifie si tous les albums présents sur le disque sont également présents dans la base de datos de
    Beets. Si un album manquant est trouvé, il est ajouté à la liste manuelle de musique si celle-ci n'est pas définie.

    :return: Une liste des chemins d'albums manquants
    """
    logger.info(f"📅 CHECK PATHS IN BEETS : {datetime.now().strftime('%d-%m-%Y')}")
    logger.info("--- (vérifie si tous les albums sont biens connus de Beets) ---")

    music_base = Path(MUSIC_BASE_PATH)
    all_album_paths = [p for p in music_base.glob("*/*") if p.is_dir()]
    logger.info(f"📁 Albums trouvés sur disque : {len(all_album_paths)}")

    expected_paths = {
        str(Path(BEETS_MUSIC) / p.relative_to(MUSIC_BASE_PATH)) for p in all_album_paths
    }
    # beet_output = get_beet_list("list", ["-a", "-f", "$path"], logger=logger)
    beet_output = get_beet_list(
        album=True, format=True, format_fields="$path", output_file=False, logger=logger
    )
    if beet_output is None:
        logger.error("❌ Impossible de récupérer la liste Beets.")
        return

    beet_paths = set(beet_output)

    missing = sorted(expected_paths - beet_paths)
    logger.info(f"🛑 Albums absents de Beets : {len(missing)}")

    if not missing:
        logger.info("✅ Tous les albums sont présents dans Beets.")
        return

    if BEETS_MANUAL_LIST:
        try:
            existing = set()
            if os.path.isfile(BEETS_MANUAL_LIST):
                with open(BEETS_MANUAL_LIST, encoding="utf-8") as f:
                    existing = {line.strip() for line in f if line.strip()}

            combined = sorted(existing.union(missing))
            with open(BEETS_MANUAL_LIST, "w", encoding="utf-8") as f:
                for path in combined:
                    f.write(path + "\n")

            logger.info(
                f"📄 {len(missing)} chemins ajoutés à la liste manuelle : {BEETS_MANUAL_LIST}"
            )
        except Exception as e:
            logger.error(f"❌ Erreur lors de l’écriture dans {BEETS_MANUAL_LIST} : {e}")
    else:
        logger.warning("Aucune variable BEETS_MANUAL_LIST définie.")

    logger.info("🏁 CHECK PATHS IN BEETS : TERMINE !! \n\n")
    return missing


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Détecte les albums manquant dans la base Beet."
    )
    args = parser.parse_args()
    check_missing_album_paths()
