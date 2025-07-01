from pathlib import Path
import unicodedata
import re
import shutil
from utils.logger import get_logger, with_child_logger
from utils.utils_div import ensure_to_path, convert_path_format
from utils.config import ESSENTIA_TEMP_AUDIO, ESSENTIA_TEMP_JSON, ESSENTIA_SAV_JSON, MAX_SAFENAME_LENGTH

def generate_mode_text(count=0, missing_features=False, is_edm=False, missing_field=None, path_contains=None):
# 🔤 Générer un texte explicite du mode actif
        mode_label = []
        if count > 0:
            mode_label.append(f"Traitement de {count} morceaux")
        else:
            mode_label.append("Traitement de tous les morceaux")
            
        if missing_features:
            mode_label.append("absents de audio_features")
        if is_edm:
            mode_label.append("EDM uniquement")
        if missing_field:
            mode_label.append(f"champ manquant : {missing_field}")
        if path_contains:
            mode_label.append(f"path contient « {path_contains} »")

        mode_text = " | ".join(mode_label) if mode_label else "Tous les morceaux"
        return mode_text

@with_child_logger
def prepare_track_paths(track, logger=None):
    try:
        track_id, raw_path, artist, album, title = track
        path = Path(convert_path_format(ensure_to_path(raw_path), to_beets=False))
        if not path.exists():
            logger.warning(f"Fichier introuvable : {path}")
            return None

        safe_name = f"{track_id}_{sanitize_filename(artist)}_{sanitize_filename(album)}_{sanitize_filename(title)}"
        # Tronque si trop long
        if len(safe_name) > MAX_SAFENAME_LENGTH:
            safe_name = safe_name[:MAX_SAFENAME_LENGTH]
        temp_audio = Path(ESSENTIA_TEMP_AUDIO) / f"{safe_name}{path.suffix}"
        temp_json = Path(ESSENTIA_TEMP_JSON) / f"{safe_name}.json"
        return track_id, path, safe_name, temp_audio, temp_json
    except Exception as e:
        logger.error(f"Erreur préparation chemins : {e}")
        raise
    
@with_child_logger
def process_audio_file(original_path, temp_audio, logger=None):
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

@with_child_logger
def clean_temp_files(*paths, logger=None):
    for path in paths:
        try:
            if path.exists():
                path.unlink()
        except Exception as e:
            logger.warning(f"Erreur suppression fichier temporaire : {path} -> {e}")

@with_child_logger
def archive_json_result(track_id: int, safe_name: str, logger=None):
    """
    Déplace un JSON de `temp_folder` vers `archive_base/XXXX/` en fonction de track_id
    """
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
