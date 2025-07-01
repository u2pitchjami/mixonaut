import subprocess
from pathlib import Path
from utils.logger import get_logger, with_child_logger

@with_child_logger
def process_beets_batch(file_path: str, logger = None) -> None:
    path_list = Path(file_path)
    if not path_list.exists():
        logger.error(f"Fichier introuvable : {file_path}")
        return

    with path_list.open("r", encoding="utf-8") as f:
        for line in f:
            directory = line.strip()
            if directory:
                run_command(f'beet import "{directory}"')
