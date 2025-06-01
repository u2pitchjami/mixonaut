from pathlib import Path
import unicodedata
import re
import shutil
from utils.logger import get_logger
from utils.utils_div import ensure_to_path, convert_path_format
from utils.config import ESSENTIA_TEMP_AUDIO, ESSENTIA_TEMP_JSON, ESSENTIA_SAV_JSON

logname = __name__.split(".")[-1]

def prepare_track_paths(track, logname=logname):
    logger = get_logger(logname)
    try:
        track_id, raw_path, artist, album, title = track
        path = Path(convert_path_format(ensure_to_path(raw_path), to_beets=False))
        if not path.exists():
            logger.warning(f"Fichier introuvable : {path}")
            return None

        safe_name = f"{track_id}_{sanitize_filename(artist)}_{sanitize_filename(album)}_{sanitize_filename(title)}"
        temp_audio = Path(ESSENTIA_TEMP_AUDIO) / f"{safe_name}{path.suffix}"
        temp_json = Path(ESSENTIA_TEMP_JSON) / f"{safe_name}.json"
        return track_id, path, safe_name, temp_audio, temp_json
    except Exception as e:
        logger.error(f"Erreur préparation chemins : {e}")
        raise

def process_audio_file(original_path, temp_audio, logname=logname):
    logger = get_logger(logname)
    try:
        shutil.copy(original_path, temp_audio)
        return True
    except Exception as e:
        logger.error(f"Erreur copie fichier audio : {e}")
        return False

def sanitize_filename(name: str) -> str:
    # Enlève les accents
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    # Garde uniquement lettres, chiffres, tirets, underscores
    name = re.sub(r"[^\w\-]", "_", name)
    # Remplace multiples underscores par un seul
    name = re.sub(r"__+", "_", name)
    return name.strip("_").lower()

def clean_temp_files(*paths, logname=logname):
    logger = get_logger(logname)
    for path in paths:
        try:
            if path.exists():
                path.unlink()
        except Exception as e:
            logger.warning(f"Erreur suppression fichier temporaire : {path} -> {e}")


def archive_json_result(track_id: int, safe_name: str, logname=logname):
    """
    Déplace un JSON de `temp_folder` vers `archive_base/XXXX/` en fonction de track_id
    """
    logger = get_logger(logname)
    # Dossier de destination
    target_folder = Path(ESSENTIA_SAV_JSON) / f"{(track_id // 1000) * 1000:04d}"
    target_folder.mkdir(parents=True, exist_ok=True)

    # Fichier source et destination
    source = Path(ESSENTIA_TEMP_JSON) / f"{safe_name}.json"
    dest = target_folder / f"{safe_name}.json"

    if not source.exists():
        logger.warning(f"❌ JSON temporaire non trouvé pour track {track_id} : {source}")
        return

    try:
        shutil.copy(source, dest)
        logger.debug(f"✅ JSON archivé : {dest}")
    except Exception as e:
        logger.warning(f"Erreur archivage JSON {track_id} : {e}")
