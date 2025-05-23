import subprocess
from typing import Dict, Set
from utils.config import MUSIC_BASE_PATH, BEETS_MUSIC
from utils.logger import get_logger
import os



# Configuration (à adapter)
IMAGE_NAME = "beets-xtractor:latest_test2"
HOST_MUSIC_DIR = MUSIC_BASE_PATH
CONTAINER_MUSIC_DIR = BEETS_MUSIC

def write_tags_docker(path: str, track_features: Dict, tags_to_write: Set[str], logname="Mixonaut") -> None:
    logger = get_logger(logname)
    
    if not os.path.isfile(path):
        logger.error(f"Fichier introuvable : {path}")
        return

    ext = os.path.splitext(path)[1].lower()
    relative_path = os.path.relpath(path, HOST_MUSIC_DIR)
    container_path = os.path.join(CONTAINER_MUSIC_DIR, relative_path)

    tag_args = []
    for tag in tags_to_write:
        value = track_features.get(tag)
        if value is not None:
            if ext == ".flac":
                tag_str = f"{tag.upper()}={value}"
            else:
                tag_str = f"{tag.upper()}:{value}"
            
            tag_args.append(tag_str)

    if not tag_args:
        logger.warning(f"Aucun tag à écrire pour {path}")
        return

    try:
        if ext == ".flac":
            # Construction de la commande metaflac
            tag_cmds = [f"metaflac --set-tag=\"{tag}\" \"{container_path}\"" for tag in tag_args]
            full_cmd = " && ".join(tag_cmds)
        elif ext == ".mp3":
            # Construction de la commande eyeD3
            tag_cmds = [f"--user-text-frame=\"{tag}\"" for tag in tag_args]
            full_cmd = f"eyeD3 {' '.join(tag_cmds)} \"{container_path}\""
        else:
            logger.error(f"Format non supporté : {ext}")
            return

        # Appel docker run
        cmd = [
            "docker", "run", "--rm",
            "-v", f"{HOST_MUSIC_DIR}:{CONTAINER_MUSIC_DIR}",
            IMAGE_NAME,
            "bash", "-c", full_cmd
        ]

        logger.info(f"Exécution Docker : {' '.join(cmd)}")
        subprocess.run(cmd, check=True)

    except subprocess.CalledProcessError as e:
        logger.error(f"Erreur lors de l'écriture des tags dans {path} : {e}")

