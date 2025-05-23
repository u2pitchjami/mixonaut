import os
from datetime import datetime
from beets_utils.commands import run_beet_command
from beets_utils.extract_paths_from_file import extract_paths_from_file
from utils.logger import get_logger
logger = get_logger("Beets_batch")

def run_beets_batch_command(
    source_file: str,
    beet_command: str,
    args_template: list[str],
    extraction_mode: str = "path_extract",
    dry_run: bool = False
) -> None:
    """
    Extrait les chemins depuis un fichier, puis exécute une commande Beets personnalisée sur chacun.
    Le fichier temporaire utilisé est géré automatiquement.

    :param source_file: Fichier d’origine (log ou brut)
    :param beet_command: Commande Beets à exécuter (ex: 'write', 'remove', 'update')
    :param args_template: Liste d’arguments avec placeholder '{path}'
    :param extraction_mode: Mode d’extraction (ex: 'path_extract', 'skip')
    :param dry_run: Mode simulation (dry-run)
    """
    logger.info(f"📅 BEETS BATCH : {datetime.now().strftime('%d-%m-%Y')}")
    output_file = "beet_batch_output.txt"
    extract_paths_from_file(source_file, output_file, mode=extraction_mode, logname="Beets_batch")

    if not os.path.isfile(output_file):
        logger.error(f"Fichier des chemins introuvable après extraction : {output_file}")
        return

    try:
        with open(output_file, "r", encoding="utf-8") as f:
            paths = [line.strip() for line in f if line.strip()]

        if not paths:
            logger.info("Aucun chemin à traiter après extraction.")
            return

        logger.info(f"{len(paths)} chemins à traiter avec beet {beet_command}.")

        for path in paths:
            args = [arg.replace("{path}", path) for arg in args_template]

            if dry_run:
                logger.info(f"[SIMULATION] beet {beet_command} {' '.join(args)}")
            else:
                output = run_beet_command(command=beet_command, args=args, capture_output=True, dry_run=dry_run, logname="Beets_batch")
                logger.info(f"output {output}")
    except Exception as e:
        logger.error(f"Erreur durant le traitement beet en masse : {e}")

if __name__ == "__main__":
    run_beets_batch_command(
        source_file="beet_works.txt",
        beet_command="xtractor",
        args_template=["{path}"],
        extraction_mode="path_extract",
        dry_run=False
    )