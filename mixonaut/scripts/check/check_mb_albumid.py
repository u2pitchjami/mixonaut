"""2025-08-20 - scripts de vérification que tous les albums aient un id musicbrainz."""

import argparse
from datetime import datetime

from mixonaut.beets_utils.commands.check_and_fix_utils import is_missing_mb_albumid
from mixonaut.beets_utils.commands.commands import get_beet_list
from mixonaut.utils.logger import get_logger
from mixonaut.utils.safe_runner import safe_main

logger = get_logger("Check_Musicbrainz")


@safe_main
def check_mb_albumid(artist: str | None = None) -> None:
    """
    Check if all albums in the specified artist have a MusicBrainz ID.

    This function queries the Beet library for a list of albums, then checks each one
    to see if it has a valid MusicBrainz ID. If an album is missing an ID, it is added
    to a set of directories without IDs. At the end, all albums without IDs are printed
    out.

    Parameters:
        artist (str): The artist to query for albums (optional)

    Returns:
        None
    """
    logger.info(f"📅 CHECK MB_ALBUMID : {datetime.now().strftime('%d-%m-%Y')}")
    logger.info("--- (vérifie si tous les albums sont reliés à Musicbrainz) ---")

    lines = get_beet_list(
        query=artist,
        album=True,
        format=True,
        format_fields="$path|$mb_albumid",
        logger=logger,
    )
    if not lines:
        return

    logger.info(f"--- Nombre d'albums à contrôler : {len(lines)} ---")
    # Étape 1 : détecter les albums sans genre
    dirs_without_mb_albumid = set()
    all_album_dirs = set()

    for line in lines:
        parts = line.split("|")
        if len(parts) != 2:
            continue

        path, mb_albumid = (p.strip() for p in parts)
        all_album_dirs.add(path)
        mb_albumid_ok = is_missing_mb_albumid(mb_albumid)

        if not mb_albumid_ok:
            dirs_without_mb_albumid.add(path)

    # ✅ Affichage une fois la boucle terminée
    if dirs_without_mb_albumid:
        logger.info(f"⚠️ Albums sans mb_albumid : {len(dirs_without_mb_albumid)}")
        for d in sorted(dirs_without_mb_albumid):
            logger.info(f" - {d}")
    else:
        logger.info("👌 Aucun album sans mb_albumid 🍾")

    logger.info("🏁 CHECK MB_ALBUMID : TERMINE !! \n\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Vérifie que tous les albums Beet aient un mb_albumid"
    )
    parser.add_argument("--artist", help="Limiter à un artiste spécifique (facultatif)")
    args = parser.parse_args()

    check_mb_albumid(artist=args.artist)
