import os
import csv
import random
import argparse
from utils.config import REPORT_PATH
from datetime import datetime
from utils.logger import get_logger
from beets_utils.commands import get_beet_list, run_beet_command

def append_to_csv_report(rows: list[dict], filename: str = REPORT_PATH):
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    header = ["date", "album", "path", "message"]
    file_exists = os.path.exists(filename)

    with open(filename, mode="a", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=header)
        if not file_exists:
            writer.writeheader()
        writer.writerows(rows)

def check_random_albums(n: int = 3) -> None:
    logger = get_logger("Check_Random_Bad_Dirs")
    logger.info(f"📅 CHECK RANDOM BAD DIRS : {datetime.now().strftime('%d-%m-%Y')}")
    
    # Liste des albums
    album_paths = get_beet_list(
    query=None,
    format_fields='$path',
    album=True,
    format=True,
    logger=logger
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
            capture_output=True,
            check=False,
            logger=logger
        )
        timestamp = datetime.now().isoformat()
        stdout = result.get("stdout", "").strip()

        if stdout and stdout.lower() != "all tasks finished!":
            logger.warning(stdout)
            message = stdout.replace("\n", " ⏎ ")
            csv_rows.append({
                "date": timestamp,
                "album": album_name,
                "path": album_dir,
                "message": message
            })

        stderr = result.get("stderr", "").strip()
        if stderr:
            logger.error(stderr)

    if csv_rows:
        append_to_csv_report(csv_rows)
        logger.info(f"{len(csv_rows)} erreur(s) ajoutée(s) au rapport CSV.")

    logger.info(f"🏁 CHECK RANDOM BAD DIRS : TERMINE !! \n\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Check aléatoirement des albums via le plugin bad")
    parser.add_argument("--n", default="10", type=int, help="Nb d'albums à checker")
    args = parser.parse_args()
    check_random_albums(n=args.n)