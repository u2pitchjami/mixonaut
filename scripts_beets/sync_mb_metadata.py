import argparse
from datetime import datetime
from beets_utils.commands import run_beet_command
from utils.logger import get_logger
from utils.safe_runner import safe_main

@safe_main
def sync_metadata(target_path=None, dry_run=False):
    logger = get_logger("Musicbrainz_Sync")
        
    logger.info(f"📅 SYNC MUSICBRAINZ : {datetime.now().strftime('%d-%m-%Y')}")
    logger.info("--- (synchronise les données avec la base Musicbrainz) ---")
    scope = target_path if target_path else "toute la base"
    logger.info(f"🎯 Portée : {scope}")

    mbsync = run_beet_command(command="mbsync", args=[target_path], interactive=False, dry_run=dry_run, logger=logger)
    logger.debug(mbsync)
    run_beet_command(command="write -f", args=[target_path], interactive=True, dry_run=dry_run, logger=logger)
    run_beet_command(command="move", args=[target_path], interactive=True, dry_run=dry_run, logger=logger)

    logger.info(f"🏁 SYNC MUSICBRAINZ : TERMINE !! \n\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sync Beets via MB (globale ou ciblée)")
    parser.add_argument("--path", help="Chemin d'un dossier album (sinon toute la base)")
    parser.add_argument("--dry-run", action="store_true", help="Simulation sans modification")
    args = parser.parse_args()

    sync_metadata(target_path=args.path, dry_run=args.dry_run)
