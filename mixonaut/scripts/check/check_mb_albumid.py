"""2025-08-20 - scripts de vérification que tous les albums aient un id musicbrainz."""

import argparse
from datetime import datetime
from pathlib import Path
from mixonaut.beets_utils.commands.check_and_fix_utils import is_missing_mb_albumid
from mixonaut.beets_utils.commands.commands import get_beet_list
from mixonaut.utils.logger import get_logger
from mixonaut.utils.safe_runner import safe_main

logger = get_logger("Check_Musicbrainz")


@safe_main
def check_mb_albumid(artist: str | None = None) -> None:
    """
    Vérifie si tous les albums ont un MusicBrainz Album ID.

    On interroge les items Beets, puis on remonte au dossier album avec Path(path).parent. Si une seule track d'un album
    n'a pas de mb_albumid, l'album est signalé.
    """
    logger.info(f"📅 CHECK MB_ALBUMID : {datetime.now().strftime('%d-%m-%Y')}")
    logger.info("--- (vérifie si tous les albums sont reliés à Musicbrainz) ---")

    lines = get_beet_list(
        query=artist,
        album=False,
        format=True,
        format_fields="$path|$mb_albumid",
        logger=logger,
    )
    if not lines:
        return

    dirs_without_mb_albumid = set()
    all_album_dirs = set()

    for line in lines:
        parts = line.split("|")
        if len(parts) != 2:
            continue

        path, mb_albumid = (p.strip() for p in parts)

        if not path:
            continue

        album_dir = Path(path).parent.as_posix()
        all_album_dirs.add(album_dir)

        if is_missing_mb_albumid(mb_albumid):
            dirs_without_mb_albumid.add(album_dir)

    logger.info(f"--- Nombre d'albums à contrôler : {len(all_album_dirs)} ---")

    if dirs_without_mb_albumid:
        logger.info(
            f"⚠️ Albums avec au moins une track sans mb_albumid : {len(dirs_without_mb_albumid)}"
        )
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
