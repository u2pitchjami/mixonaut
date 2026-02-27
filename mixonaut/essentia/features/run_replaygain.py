#!/usr/bin/env python3
"""
2025-08-20.

modules qui lance le replaygain via docker.
"""

import subprocess
import sys
from pathlib import Path

from mixonaut.utils.config import IMAGE_ESSENTIA
from mixonaut.utils.logger import LoggerProtocol, ensure_logger, with_child_logger


@with_child_logger
def run_replaygain_in_container(
    audio_path: Path,
    json_out_path: Path,
    profile_path: Path,
    logger: LoggerProtocol | None = None,
) -> None:
    """
    Launches the replaygain process in a Docker container.

    Parameters:
        audio_path (str): The path to the input audio file.
        json_out_path (str): The path to the output JSON file.
        profile_path (str): The path to the profile directory.
        logger (LoggerProtocol | None, optional): The logger instance. Defaults to None.

    Returns:
        None
    """
    logger = ensure_logger(logger, __name__)
    # Vérifie que les fichiers existent
    audio = Path(audio_path)
    json_out = Path(json_out_path)
    profile = Path(profile_path)

    if not audio.exists():
        logger.error(f"❌ Audio file not found: {audio}")
        sys.exit(1)

    # Préparation du montage
    temp_dir = audio.parent.resolve()

    # Construction de la commande Docker
    docker_cmd = [
        "docker",
        "run",
        "--rm",
        "-v",
        f"{temp_dir}:/app/music",
        "-v",
        f"{profile}:/app/profile",
        IMAGE_ESSENTIA,
        "python3",
        "/usr/local/bin/add_replaygain.py",  # ou "python3 /app/add_replaygain.py" si pas executable
        f"/app/music/{audio.name}",
        f"/app/music/{json_out.name}",
    ]

    logger.debug(f"▶️ Commande : {' '.join(docker_cmd)}")

    try:
        subprocess.run(docker_cmd, check=True)
        logger.debug("✅ ReplayGain calculé avec succès.")
    except subprocess.CalledProcessError as e:
        logger.error("❌ Erreur lors de l'exécution du conteneur : %s", e)
        raise
