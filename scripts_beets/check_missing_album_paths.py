import os
import argparse
from pathlib import Path
from datetime import datetime
from utils.logger import get_logger
from beets_utils.commands import get_beet_list
from utils.config import MUSIC_BASE_PATH, BEETS_MUSIC, BEETS_MANUAL_LIST

logger = get_logger("Check_Album_in_Beets")

def check_missing_album_paths():
    logger.info(f"📅 CHECK PATHS IN BEETS : {datetime.now().strftime('%d-%m-%Y')}")
    logger.info("--- (vérifie si tous les albums sont biens connus de Beets) ---")

    music_base = Path(MUSIC_BASE_PATH)
    all_album_paths = [
        p for p in music_base.glob("*/*") if p.is_dir()
    ]
    logger.info(f"📁 Albums trouvés sur disque : {len(all_album_paths)}")

    expected_paths = {
        str(Path(BEETS_MUSIC) / p.relative_to(MUSIC_BASE_PATH))
        for p in all_album_paths
    }
    #beet_output = get_beet_list("list", ["-a", "-f", "$path"], logger=logger)
    beet_output = get_beet_list(album=True, format=True, format_fields="$path", output_file=False, logger=logger)
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
                with open(BEETS_MANUAL_LIST, "r", encoding="utf-8") as f:
                    existing = set(line.strip() for line in f if line.strip())

            combined = sorted(existing.union(missing))
            with open(BEETS_MANUAL_LIST, "w", encoding="utf-8") as f:
                for path in combined:
                    f.write(path + "\n")

            logger.info(f"📄 {len(missing)} chemins ajoutés à la liste manuelle : {BEETS_MANUAL_LIST}")
        except Exception as e:
            logger.error(f"❌ Erreur lors de l’écriture dans {BEETS_MANUAL_LIST} : {e}")
    else:
        logger.warning("Aucune variable BEETS_MANUAL_LIST définie.")

    logger.info(f"🏁 CHECK PATHS IN BEETS : TERMINE !! \n\n")
    return missing

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Détecte les albums manquant dans la base Beet.")
    args = parser.parse_args()
    check_missing_album_paths()