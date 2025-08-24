"""2025-08-20 - script de synchronisation beets avec musicbrainz."""

import argparse
from datetime import datetime

from mixonaut.beets_utils.commands.commands import run_beet_command
from mixonaut.utils.logger import get_logger
from mixonaut.utils.safe_runner import safe_main


@safe_main
def sync_metadata(target_path: str | None = None, dry_run: bool = False) -> None:
    """
    Synchronise les données de Musicbrainz avec Beets.

    Ce script synchronise les données de Musicbrainz avec la base Beets en utilisant le commandement `mbsync`.

    Args:
        target_path (str): Le chemin vers la cible (par défaut, la base toute).
        dry_run (bool): Si True, effectue uniquement une vérification des commandes sans les exécuter.

    Returns:
        None
    """
    logger = get_logger("Musicbrainz_Sync")

    logger.info(f"📅 SYNC MUSICBRAINZ : {datetime.now().strftime('%d-%m-%Y')}")
    logger.info("--- (synchronise les données avec la base Musicbrainz) ---")
    scope = target_path if target_path else "toute la base"
    logger.info(f"🎯 Portée : {scope}")

    run_beet_command(
        command="mbsync",
        args=[target_path] if target_path else None,
        interactive=False,
        dry_run=dry_run,
        logger=logger,
    )
    run_beet_command(
        command="write -f",
        args=[target_path] if target_path else None,
        interactive=True,
        dry_run=dry_run,
        logger=logger,
    )
    run_beet_command(
        command="move",
        args=[target_path] if target_path else None,
        interactive=True,
        dry_run=dry_run,
        logger=logger,
    )

    logger.info("🏁 SYNC MUSICBRAINZ : TERMINE !! \n\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Sync Beets via MB (globale ou ciblée)"
    )
    parser.add_argument(
        "--path", help="Chemin d'un dossier album (sinon toute la base)"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Simulation sans modification"
    )
    args = parser.parse_args()

    sync_metadata(target_path=args.path, dry_run=args.dry_run)
