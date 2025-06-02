from utils.config import ESSENTIA_TEMP_AUDIO, PROF_ESSENTIA, ESSENTIA_MAPPING, IMAGE_ESSENTIA, BEETS_CONFIG_DIR
import subprocess
from pathlib import Path
import json
from utils.logger import get_logger

logname = __name__.split(".")[-1]

def run_essentia_extraction(audio_path: Path, json_path: Path, profile_path: Path, logname=logname) -> bool:
    """Lance l'extraction via le script Bash contenant l'appel à essentia_streaming_extractor_music"""
    logger = get_logger(logname)
    
    #script_path = Path(SCRIPT_PATH_ESSENTIA)
    profile_dir = Path(PROF_ESSENTIA).parent

        
    # if not Path(script_path).exists():
    #     logger.error(f"Script Bash introuvable : {script_path}")
    #     return False

    try:
        logger.info(f"▶️ Lancement extraction pour : {audio_path.name}")
        
        # Construction de la commande Docker
        docker_cmd = [
            "docker", "run", "--rm",
            "-v", f"{str(ESSENTIA_TEMP_AUDIO)}:/app/music",
            "-v", f"{str(profile_dir)}:/app/profile",
            "-v", f"{str(BEETS_CONFIG_DIR)}:/app/config",
            IMAGE_ESSENTIA,
            "essentia_streaming_extractor_music",  # ou "python3 /app/add_replaygain.py" si pas executable
            str(audio_path),
            str(json_path),
            str(profile_path)
        ]
        
        logger.debug(f"▶️ Commande : {' '.join(docker_cmd)}")
        
        result = subprocess.run(
            docker_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
            text=True
        )
        logger.info(f"✅ Extraction terminée pour {audio_path.name}")
        return True

    except Exception as e:
        logger.error(f"❌ Erreur durant l'extraction essentia : {audio_path.name}")
        raise

def get_nested(data, path):
    try:
        for key in path:
            data = data[key]
        return data
    except (KeyError, TypeError):
        raise

def parse_essentia_json(json_path, logname=logname):
    """Parse le JSON généré par Essentia et retourne les champs mappés"""
    logger = get_logger(logname)
    try:
        with open(json_path, "r") as f:
            data = json.load(f)
    except Exception as e:
        logger.error(f"Erreur lecture JSON Essentia : {e}")
        raise

    result = {}
    for field, path in ESSENTIA_MAPPING.items():
        value = get_nested(data, path)
        if value is None:
            logger.warning(f"Champ manquant ou invalide : {field} (path: {path})")
            return
        result[field] = value

    return result
