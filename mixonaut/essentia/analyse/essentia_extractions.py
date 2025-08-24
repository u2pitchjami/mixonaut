"""
2025-08-20.

modules de run modules de run essentia + parsing du json .
"""

import json
import subprocess
from pathlib import Path
from typing import Any

from mixonaut.utils.config import (
    BEETS_CONFIG_DIR,
    ESSENTIA_MAPPING,
    ESSENTIA_TEMP_AUDIO,
    IMAGE_ESSENTIA,
    PROF_ESSENTIA,
)
from mixonaut.utils.logger import LoggerProtocol, ensure_logger, with_child_logger


@with_child_logger
def run_essentia_extraction(
    audio_path: Path,
    json_path: Path,
    profile_path: Path,
    logger: LoggerProtocol | None = None,
) -> tuple[str, str | None]:
    """
    Lance l'extraction via le script Bash contenant l'appel à essentia_streaming_extractor_music.
    """
    logger = ensure_logger(logger, __name__)
    profile_dir = Path(PROF_ESSENTIA).parent
    try:
        logger.debug(f"▶️ Lancement extraction pour : {audio_path.name}")
        # Construction de la commande Docker
        docker_cmd = [
            "docker",
            "run",
            "--rm",
            "-v",
            f"{str(ESSENTIA_TEMP_AUDIO)}:/app/music",
            "-v",
            f"{str(profile_dir)}:/app/profile",
            "-v",
            f"{str(BEETS_CONFIG_DIR)}:/app/config",
            IMAGE_ESSENTIA,
            "essentia_streaming_extractor_music",  # ou "python3 /app/add_replaygain.py" si pas executable
            str(audio_path),
            str(json_path),
            str(profile_path),
        ]
        logger.debug(f"▶️ Commande : {' '.join(docker_cmd)}")

        try:
            subprocess.run(
                docker_cmd,
                capture_output=True,
                check=True,
                text=True,
            )
        except subprocess.CalledProcessError as exc:
            # Essentiel: afficher exc.stderr (message d'Essentia ou du conteneur)
            # stdout = (exc.stdout or "").strip()
            stderr = (exc.stderr or "").strip().splitlines()[-1]
            logger.error("Command failed: STDERR:%s", stderr or "(empty)")
            return "KO_Audio", stderr

        logger.debug(f"✅ Extraction terminée pour {audio_path.name}")
        # print(f"result : {result}")
        return "OK", None

    except Exception as e:
        logger.error(
            f"❌ Erreur durant l'extraction essentia : {audio_path.name} : {e}"
        )
        raise


def get_nested(data: dict[str, Any], path: Any) -> dict[str, Any]:
    """
    Recursively retrieves nested data from a dictionary.
    Args:
        data (dict): The dictionary to retrieve data from.
        path (list of str): A list of keys representing the path to the desired data.

    Returns:
        any: The retrieved data or raises a KeyError/TypeError if the path is invalid.

    Raises:
        KeyError: If the path does not exist in the dictionary.
        TypeError: If the value at the end of the path is not a valid type (e.g., not a dict, list, etc.).
    """
    try:
        for key in path:
            data = data[key]
        return data
    except (KeyError, TypeError):
        raise


@with_child_logger
def parse_essentia_json(
    json_path: Path, logger: LoggerProtocol | None = None
) -> dict[str, Any]:
    """
    Parse le JSON généré par Essentia et retourne les champs mappés.
    """
    logger = ensure_logger(logger, __name__)
    try:
        with open(json_path) as f:
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
