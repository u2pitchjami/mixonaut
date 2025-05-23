from utils.config import ESSENTIA_TEMP_AUDIO, ESSENTIA_TEMP_JSON, SCRIPT_PATH_ESSENTIA, PROF_ESSENTIA, ESSENTIA_MAPPING
import subprocess
from pathlib import Path
import json
from utils.logger import get_logger

def run_essentia_extraction(audio_path: Path, json_path: Path, profile_path: Path, logname="Mix_Assist") -> bool:
    """Lance l'extraction via le script Bash contenant l'appel à essentia_streaming_extractor_music"""
    logger = get_logger(logname)
        
    if not Path(SCRIPT_PATH_ESSENTIA).exists():
        logger.error(f"Script Bash introuvable : {SCRIPT_PATH_ESSENTIA}")
        return False

    try:
        logger.info(f"▶️ Lancement extraction pour : {audio_path.name}")
        result = subprocess.run(
            [str(SCRIPT_PATH_ESSENTIA), str(audio_path), str(json_path), str(profile_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
            text=True
        )
        logger.info(f"✅ Extraction terminée pour {audio_path.name}")
        return True

    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Erreur durant l'extraction : {audio_path.name}")
        logger.error(e.stderr)
        return False

def get_nested(data, path):
    try:
        for key in path:
            data = data[key]
        return data
    except (KeyError, TypeError):
        return None

def parse_essentia_json(json_path, logname="Mix_Assist"):
    logger = get_logger(logname)
    try:
        with open(json_path, "r") as f:
            data = json.load(f)
    except Exception as e:
        logger.error(f"Erreur lecture JSON Essentia : {e}")
        return {}

    result = {}
    for field, path in ESSENTIA_MAPPING.items():
        value = get_nested(data, path)
        if value is None:
            logger.warning(f"Champ manquant ou invalide : {field} (path: {path})")
        result[field] = value

    return result
