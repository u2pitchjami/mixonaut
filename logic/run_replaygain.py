#!/usr/bin/env python3

import subprocess
import sys
from pathlib import Path

def run_replaygain_in_container(audio_path: str, json_out_path: str):
    # Vérifie que les fichiers existent
    audio = Path(audio_path)
    json_out = Path(json_out_path)

    if not audio.exists():
        print(f"❌ Audio file not found: {audio}")
        sys.exit(1)

    # Préparation du montage
    temp_dir = audio.parent.resolve()
    profile_dir = Path("/home/pipo/data/appdata/mixonaut/essentia").resolve()

    # Construction de la commande Docker
    docker_cmd = [
        "docker", "run", "--rm",
        "-v", f"{temp_dir}:/app/music",
        "-v", f"{profile_dir}:/app/profile",
        "essentia_docker:latest",
        "python3", "/usr/local/bin/add_replaygain.py",  # ou "python3 /app/add_replaygain.py" si pas executable
        f"/app/music/{audio.name}",
        f"/app/music/{json_out.name}"
    ]

    print(f"▶️ Commande : {' '.join(docker_cmd)}")

    try:
        subprocess.run(docker_cmd, check=True)
        print("✅ ReplayGain calculé avec succès.")
    except subprocess.CalledProcessError as e:
        print("❌ Erreur lors de l'exécution du conteneur :")
        print(e)

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Utilisation : python run_replaygain.py <audio_file> <json_out>")
        sys.exit(1)

    run_replaygain_in_container(sys.argv[1], sys.argv[2])
