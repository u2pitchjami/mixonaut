import subprocess
from pathlib import Path
from typing import List
from utils.config import AUDIO_EXTENSIONS
from beets_utils.commands import get_beet_list
from utils.utils_div import convert_path_format
from utils.logger import get_logger

logger = get_logger("Beets_Utils")


def get_album_paths_from_beets() -> List[str]:
    """
    Utilise get_beet_list pour récupérer tous les chemins d'albums dans la base Beets.
    """
    lines = get_beet_list(query=None, album=True, format=True, format_fields="$path", logname="Beets_Utils")
    return [line for line in lines if line.strip()]

def get_music_files_from_path(folder_path: str) -> List[Path]:
    """
    Renvoie la liste des fichiers audio dans un dossier donné (récursivement).
    """
    original_path = folder_path
    folder_path = convert_path_format(path=folder_path, to_beets=False)
    logger.debug(f"Conversion du chemin : {original_path} => {folder_path}")

    folder = Path(folder_path)
    if not folder.exists() or not folder.is_dir():
        return []

    return [
        file for file in folder.rglob("*")
        if file.is_file() and file.suffix.lower() in AUDIO_EXTENSIONS
    ]
