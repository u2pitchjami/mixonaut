"""
2025-08-20.

modules de run modules de run essentia + parsing du json .
"""

import json
import subprocess
from pathlib import Path
from typing import Any

from mixonaut.utils.config import (
    MADMOM_MAPPING,
    MADMOM_TEMP_AUDIO,
    IMAGE_MADMOM,
)
from mixonaut.utils.logger import LoggerProtocol, ensure_logger


def run_madmom_extraction(
    audio_path: Path,
    json_path: Path,
    logger: LoggerProtocol | None = None,
) -> tuple[str, str | None]:
    """
    Lance l'extraction madmom via Docker.

    Le script du conteneur doit accepter :
    - chemin audio dans le conteneur
    - chemin JSON de sortie dans le conteneur
    """
    logger = ensure_logger(logger, __name__)
    print(
        f"[DEBUG] run_madmom_extraction audio_path={audio_path}, json_path={json_path}"
    )
    container_audio_path = Path("/app/music") / audio_path.name
    print(f"[DEBUG] container_audio_path={container_audio_path}")
    docker_cmd = [
        "docker",
        "run",
        "--rm",
        "-v",
        f"{MADMOM_TEMP_AUDIO}:/app/music:ro",
        IMAGE_MADMOM,
        str(container_audio_path),
    ]

    logger.debug("▶️ Commande madmom : %r", docker_cmd)

    try:
        result = subprocess.run(
            docker_cmd,
            capture_output=True,
            check=False,
            text=True,
        )
        if result.returncode == 0:
            logger.debug("Madmom return code: %s", result.returncode)
        else:
            logger.error("Madmom return code: %s", result.returncode)
            logger.error("Madmom stdout: %s", result.stdout)
            logger.error("Madmom stderr: %s", result.stderr)

    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or "").strip()
        stdout = (exc.stdout or "").strip()
        message = stderr or stdout or "Erreur Docker madmom inconnue"
        logger.error("❌ Madmom failed: %s", message)
        return "KO_Audio", message

    stdout = result.stdout.strip()

    if not stdout:
        message = "Madmom n'a retourné aucun JSON sur stdout."
        logger.error(message)
        return "KO_Audio", message

    try:
        data = json.loads(stdout)
    except json.JSONDecodeError as exc:
        logger.error("JSON madmom invalide : %s", stdout[:1000])
        return "KO_Audio", str(exc)

    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    logger.debug("✅ JSON madmom sauvegardé : %s", json_path)
    return "OK", None


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


def parse_madmom_json(
    json_path: Path, logger: LoggerProtocol | None = None
) -> dict[str, Any]:
    """
    Parse le JSON généré par Madmom et retourne les champs mappés.
    """
    logger = ensure_logger(logger, __name__)
    try:
        with open(json_path) as f:
            data = json.load(f)
    except Exception as e:
        logger.error(f"Erreur lecture JSON Madmom : {e}")
        raise

    result = {}
    for field, path in MADMOM_MAPPING.items():
        value = get_nested(data, path)
        if value is None:
            logger.warning(f"Champ manquant ou invalide : {field} (path: {path})")
            return
        result[field] = value

    return result
