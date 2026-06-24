"""
2020-08-20 module de traitemments de retro alim des tags fichiers.
"""

import os
import subprocess
from typing import Any

from mixonaut.utils.config import BEETS_MUSIC, IMAGE_BEETS, MUSIC_BASE_PATH
from mixonaut.utils.logger import LoggerProtocol, ensure_logger

# Configuration (à adapter)
IMAGE_NAME = IMAGE_BEETS  # Nom de l'image Docker
HOST_MUSIC_DIR = MUSIC_BASE_PATH
CONTAINER_MUSIC_DIR = BEETS_MUSIC


def write_tags_docker(
    path: str, track_features: dict[str, Any], logger: LoggerProtocol | None = None
) -> None:
    """
    This function writes tags to a music file using Docker.

    Parameters:
        path (str): The path to the music file.
        track_features (dict): A dictionary of track features,
        where each key is a tag name and each value is the corresponding feature value.
        logger (LoggerProtocol | None): An optional logger instance. If not provided, a new logger will be created.

    Returns:
        None
    """
    logger = ensure_logger(logger, __name__)
    tags_to_write = list(track_features.keys())
    logger.debug(f"tags_to_write : {tags_to_write}")

    if not os.path.isfile(path):
        logger.error(f"Fichier introuvable : {path}")
        return

    ext = os.path.splitext(path)[1].lower()
    relative_path = os.path.relpath(path, HOST_MUSIC_DIR)
    container_path = os.path.join(CONTAINER_MUSIC_DIR, relative_path)

    if not tags_to_write:
        logger.warning(f"Aucun tag à écrire pour {path}")
        return

    try:
        tag_cmds = []

        if ext == ".flac":
            for tag in tags_to_write:
                value = track_features.get(tag)
                if value is not None:
                    tag_upper = tag.upper()
                    clean_value = str(value).strip().replace("\n", " ")

                    # Vérifie si le tag existe déjà
                    try:
                        result = subprocess.run(
                            docker_metaflac_cmd(
                                container_path, ["--show-tag=" + tag_upper]
                            ),
                            capture_output=True,
                            text=True,
                            check=False,
                        )
                        tag_exists = result.stdout.strip() != ""
                        logger.debug(f"Tag {tag_upper} existe déjà : {tag_exists}")
                    except Exception as e:
                        logger.warning(
                            f"Erreur lors du test de présence du tag {tag_upper} : {e}"
                        )
                        tag_exists = False

                    if tag_exists:
                        subprocess.run(
                            docker_metaflac_cmd(
                                container_path, ["--remove-tag=" + tag_upper]
                            ),
                            capture_output=True,
                            text=True,
                            check=False,
                        )

                    subprocess.run(
                        docker_metaflac_cmd(
                            container_path, [f"--set-tag={tag_upper}={clean_value}"]
                        ),
                        capture_output=True,
                        text=True,
                        check=False,
                    )

        elif ext == ".mp3":
            for tag in tags_to_write:
                value = track_features.get(tag)
                if value is not None:
                    clean_value = str(value).strip().replace("\n", " ")
                    tag_cmds.append(f'--user-text-frame="{tag}:{clean_value}"')
            full_cmd = f'eyeD3 {" ".join(tag_cmds)} "{container_path}"'

            # Appel docker run
            cmd = [
                "docker",
                "run",
                "--rm",
                "-v",
                f"{HOST_MUSIC_DIR}:{CONTAINER_MUSIC_DIR}",
                IMAGE_NAME,
                "bash",
                "-c",
                full_cmd,
            ]

            logger.debug(f"Exécution Docker : {' '.join(cmd)}")
            subprocess.run(cmd, check=True)

        else:
            logger.error(f"Format non supporté : {ext}")
            return
    except subprocess.CalledProcessError as e:
        logger.error(f"Erreur lors de l'écriture des tags dans {path} : {e}")


def docker_metaflac_cmd(flac_path: str, operation: list[str] | str) -> list[str]:
    """
    Construct a Docker command to interact with MetaFLAC.

    Parameters
    ----------
    flac_path : str
        The path to the FLAC file within the container.
    operation : list of str
        A list of operations to perform on the FLAC file (e.g., `--show-tag`, `--remove-tag`, `--set-tag`).
    Returns
    -------
    list of str
        The constructed Docker command as a list of strings.

    Notes
    -----
    This function uses the `docker run` command to execute MetaFLAC commands within a container.
    """
    docker_path = flac_path.replace(str(HOST_MUSIC_DIR), str(CONTAINER_MUSIC_DIR))
    return [
        "docker",
        "run",
        "--rm",
        "-v",
        f"{HOST_MUSIC_DIR}:{CONTAINER_MUSIC_DIR}",
        f"{IMAGE_NAME}",
        "metaflac",
        *operation,
        docker_path,
    ]
