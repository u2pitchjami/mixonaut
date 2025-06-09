#!/usr/bin/env python3
import subprocess
import sys
from pathlib import Path
from utils.config import IMAGE_ESSENTIA
from utils.logger import get_logger

logname = __name__.split(".")[-1]

def run_replaygain_in_container(audio_path: str, json_out_path: str, profile_path: str, logname=logname):
    logger = get_logger(logname)
    # Vérifie que les fichiers existent
    audio = Path(audio_path)
    json_out = Path(json_out_path)
    profile = Path(profile_path)
    
    if not audio.exists():
        logger.error(f"❌ Audio file not found: {audio}")
        sys.exit(1)

    # Préparation du montage
    temp_dir = audio.parent.resolve()
    profile_dir = Path("/home/pipo/data/appdata/mixonaut/essentia").resolve()

    # Construction de la commande Docker
    docker_cmd = [
        "docker", "run", "--rm",
        "-v", f"{temp_dir}:/app/music",
        "-v", f"{profile}:/app/profile",
        IMAGE_ESSENTIA,
        "python3", "/usr/local/bin/add_replaygain.py",  # ou "python3 /app/add_replaygain.py" si pas executable
        f"/app/music/{audio.name}",
        f"/app/music/{json_out.name}"
    ]

    logger.debug(f"▶️ Commande : {' '.join(docker_cmd)}")

    try:
        subprocess.run(docker_cmd, check=True)
        logger.debug("✅ ReplayGain calculé avec succès.")
    except subprocess.CalledProcessError as e:
        logger.error("❌ Erreur lors de l'exécution du conteneur :")
        raise

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Utilisation : python run_replaygain.py <audio_file> <json_out>")
        sys.exit(1)

    run_replaygain_in_container(sys.argv[1], sys.argv[2])
