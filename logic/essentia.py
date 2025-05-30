from utils.config import ESSENTIA_TEMP_AUDIO, ESSENTIA_TEMP_JSON, SCRIPT_PATH_ESSENTIA, SCRIPT_PATH_REPLAYGAIN, PROF_ESSENTIA, ESSENTIA_MAPPING
import subprocess
from pathlib import Path
import json
from utils.logger import get_logger

logname = __name__.split(".")[-1]

def run_essentia_extraction(audio_path: Path, json_path: Path, profile_path: Path, logname=logname) -> bool:
    """Lance l'extraction via le script Bash contenant l'appel à essentia_streaming_extractor_music"""
    logger = get_logger(logname)
    
    script_path = Path(SCRIPT_PATH_ESSENTIA)
        
    if not Path(script_path).exists():
        logger.error(f"Script Bash introuvable : {script_path}")
        return False

    try:
        logger.info(f"▶️ Lancement extraction pour : {audio_path.name}")
        result = subprocess.run(
            [str(script_path), str(audio_path), str(json_path), str(profile_path)],
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

def get_best_key_from_essentia(track_features: dict):
    """
    Sélectionne la tonalité la plus fiable en fonction de la plus grande strength
    parmi les 3 analyseurs : edma, krumhansl, temperley.
    """
    candidates = {
        "edma": {
            "key": track_features.get("key_edma"),
            "scale": track_features.get("scale_edma"),
            "strength": track_features.get("strength_edma")
        },
        "krumhansl": {
            "key": track_features.get("key_krumhansl"),
            "scale": track_features.get("scale_krumhansl"),
            "strength": track_features.get("strength_krumhansl")
        },
        "temperley": {
            "key": track_features.get("key_temperley"),
            "scale": track_features.get("scale_temperley"),
            "strength": track_features.get("strength_temperley")
        }
    }

    best = None
    max_strength = -1

    for algo, data in candidates.items():
        if data["key"] and data["strength"] is not None:
            if data["strength"] > max_strength:
                max_strength = data["strength"]
                best = {
                    "algorithm": algo,
                    "key": data["key"],
                    "scale": data["scale"],
                    "strength": data["strength"]
                }

    return best  # dict or None

