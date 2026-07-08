"""2025-08-20 - scripts de lancement du plugin bad de beets pour identifier des pb de fichiers"""

import argparse
import csv
import os
import random
from datetime import datetime

from mixonaut.beets_utils.commands.commands import get_beet_list, run_beet_command
from mixonaut.utils.config import REPORT_PATH
from mixonaut.utils.logger import get_logger
from mixonaut.utils.safe_runner import safe_main


def append_to_csv_report(
    rows: list[dict[str, str]], filename: str = REPORT_PATH
) -> None:
    """
    Appends a list of report rows to a CSV file.

    Args:
        rows (list[dict]): The report data to append.
        filename (str): The path to the CSV file. Defaults to the value of REPORT_PATH.

    Returns:
        None
    """
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    header = ["date", "album", "path", "message"]
    file_exists = os.path.exists(filename)

    with open(filename, mode="a", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=header)
        if not file_exists:
            writer.writeheader()
        writer.writerows(rows)


@safe_main
def check_random_albums(n: int = 3) -> None:
    """
    This function checks a random selection of albums from the Beets library for potential issues.

    It uses the 'bad' command to run Beets in non-interactive mode and captures its output. If an error is found, it
    adds a new row to the report CSV file.

    :param n: The number of albums to select at random (default=3)
    """
    logger = get_logger("Check_Random_Bad_Dirs")
    logger.info(f"📅 CHECK RANDOM BAD DIRS : {datetime.now().strftime('%d-%m-%Y')}")

    # Liste des albums
    album_paths = get_beet_list(
        query=None, format_fields="$path", album=False, format=True, logger=logger
    )

    if not album_paths:
        logger.warning("Aucun album trouvé dans la bibliothèque Beets.")
        return

    logger.info(f"{len(album_paths)} albums trouvés. Sélection de {n} au hasard.")
    selected = random.sample(album_paths, min(n, len(album_paths)))
    logger.info(f"{selected}")

    csv_rows = []
    for i, album_path in enumerate(selected, start=1):
        album_dir = album_path.strip()
        album_name = os.path.basename(album_dir)
        logger.info(f"[{i}] Analyse de : {album_dir}")

        result = run_beet_command(
            command="bad",
            args=[album_dir],
            interactive=False,
            check=False,
            logger=logger,
        )
        timestamp = datetime.now().isoformat()
        stdout = result.get("stdout", "").strip()

        if stdout and stdout.lower() != "all tasks finished!":
            logger.warning(stdout)
            message = stdout.replace("\n", " ⏎ ")
            csv_rows.append(
                {
                    "date": timestamp,
                    "album": album_name,
                    "path": album_dir,
                    "message": message,
                }
            )

        stderr = result.get("stderr", "").strip()
        if stderr:
            logger.error(stderr)

    if csv_rows:
        append_to_csv_report(csv_rows)
        logger.info(f"{len(csv_rows)} erreur(s) ajoutée(s) au rapport CSV.")

    logger.info("🏁 CHECK RANDOM BAD DIRS : TERMINE !! \n\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Check aléatoirement des albums via le plugin bad"
    )
    parser.add_argument("--n", default="10", type=int, help="Nb d'albums à checker")
    args = parser.parse_args()
    check_random_albums(n=args.n)
