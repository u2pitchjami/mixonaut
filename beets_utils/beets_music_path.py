from pathlib import Path
from utils.config import AUDIO_EXTENSIONS
from beets_utils.commands import get_beet_list
from utils.utils_div import convert_path_format
from utils.logger import with_child_logger

# fonction non utilisée
@with_child_logger
def get_album_paths_from_beets(logger=None) -> list[str]:
    """
    This function retrieves all album paths from Beets database.

    It uses the `get_beet_list` function to query the database and retrieve the paths.
    The query is set to retrieve only albums (album=True), with the "$path" format field included,
    which will return the path of each album. The results are then stripped of any leading or trailing whitespace
    before being returned.

    :param logger: Optional logger instance for logging purposes.
    :return: A list of album paths as strings.
    """
    lines = get_beet_list(query=None, album=True, format=True, format_fields="$path", logger=logger)
    return [line for line in lines if line.strip()]

def get_music_files_from_path(folder_path: str) -> list[Path]:
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
