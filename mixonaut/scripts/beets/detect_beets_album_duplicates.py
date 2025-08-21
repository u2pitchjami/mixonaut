"""2025-08-20 - script d'identification d'albums potentiellement en doublons."""

import argparse
import subprocess
from collections import defaultdict
from datetime import datetime

from mixonaut.beets_utils.commands.commands import get_beet_list
from mixonaut.utils.logger import get_logger
from mixonaut.utils.safe_runner import safe_main

logger = get_logger("Beets_Check_Duplicates")


def normalize(s):
    """
    Normalize a string by stripping leading/trailing whitespace and converting to lowercase.

    Args:
        s (str): The input string to be normalized.

    Returns:
        str: The normalized string.
    """
    return s.strip().lower()


@safe_main
def detect_beets_album_duplicates():
    """
    Detects duplicate albums in the Beets database.

    This script retrieves a list of albums from Beets, then identifies any duplicates based on album title, artist, and
    release year.
    """
    logger.info(f"📅 CHECK DUPLICATES : {datetime.now().strftime('%d-%m-%Y')}")
    logger.info("--- (identifie les albums potentiellement en doublons) ---")

    try:
        result = get_beet_list(
            album=True,
            format=True,
            format_fields="$album|$albumartist|$year",
            output_file=False,
            logger=logger,
        )

    except subprocess.CalledProcessError as e:
        logger.error("Erreur lors de l'exécution de la commande 'beet list'")
        logger.error(e.stderr)
        return

    index = defaultdict(list)

    for line in result:
        parts = line.split("|")
        if len(parts) != 3:
            continue
        album, artist, year = (normalize(p) for p in parts)
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

    logger.info("🏁 CHECK DUPLICATES : TERMINE !! \n\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Détecte les albums dupliqués dans la base Beets."
    )
    args = parser.parse_args()
    detect_beets_album_duplicates()
