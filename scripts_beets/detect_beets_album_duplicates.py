import subprocess
import argparse
from datetime import datetime
from collections import defaultdict
from datetime import datetime
from beets_utils.commands import get_beet_list
from utils.logger import get_logger
logger = get_logger("Beets_duplicates")

def normalize(s):
    return s.strip().lower()

def detect_beets_album_duplicates():
    logger.info(f"📅 CHECK DUPLICATES : {datetime.now().strftime('%d-%m-%Y')}")
    logger.info("--- (identifie les albums potentiellement en doublons) ---")

    try:
        result = get_beet_list(album=True, format=True, format_fields="$album|$albumartist|$year", output_file=False, logname="Beets_duplicates")
        
    except subprocess.CalledProcessError as e:
        logger.error("Erreur lors de l'exécution de la commande 'beet list'")
        logger.error(e.stderr)
        return

    index = defaultdict(list)

    for line in result:
        parts = line.split("|")
        if len(parts) != 3:
            continue
        album, artist, year = [normalize(p) for p in parts]
        key = f"{album}|{artist}|{year}"
        index[key].append(line)

    found = False

    for key, occurrences in index.items():
        if len(occurrences) > 1:
            found = True
            album, artist, year = key.split("|")
            logger.info(f"[DOUBLON] {album} - {artist} ({year})")
            for occ in occurrences:
                logger.info(f"  - {occ}")

    if not found:
        logger.info("🌞 Aucun doublon trouvé.")

    logger.info(f"🏁 CHECK DUPLICATES : TERMINE !! \n\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Détecte les albums dupliqués dans la base Beets.")
    args = parser.parse_args()
    detect_beets_album_duplicates()
