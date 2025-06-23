import os
import argparse
import json
from essentia.essentia_extractions import parse_essentia_json
from db.essentia_queries import get_all_track_ids, insert_or_update_audio_features
from utils.config import ESSENTIA_SAV_JSON
from utils.logger import get_logger

logger = get_logger("update_features")


def build_json_path(base_path, track_id, artist, title):
    subfolder = str((track_id // 1000) * 1000)
    filename = f"{track_id}_{artist}_{title}.json".replace(" ", "_").lower()
    return os.path.join(base_path, subfolder, filename)


def main(force=False):
    base_path = ESSENTIA_SAV_JSON
    if not base_path:
        logger.error("Variable d'environnement ESSENTIA_SAV_JSON introuvable.")
        return

    # Chargement de tous les IDs présents
    track_ids = get_all_track_ids()

    for track_id in track_ids:
        # Pour générer les chemins il faudra nom + titre => ici on triche car non dispo
        # À adapter si les infos sont dans une autre table
        
        # Ici, on partira du nom du fichier directement si existant
        subfolder = str((track_id // 1000) * 1000)
        subdir = os.path.join(base_path, subfolder)

        if not os.path.isdir(subdir):
            logger.warning(f"Répertoire introuvable : {subdir}")
            continue

        json_file = next((f for f in os.listdir(subdir) if f.startswith(f"{track_id}_") and f.endswith(".json")), None)
        if not json_file:
            logger.warning(f"Fichier JSON non trouvé pour track ID {track_id} dans {subdir}")
            continue

        json_path = os.path.join(subdir, json_file)

        try:
            result = parse_essentia_json(json_path, logname="update_features")
            if not result:
                continue
            insert_or_update_audio_features(track_id, result, force=force, logname="update_features")
        except Exception as e:
            logger.error(f"Erreur traitement ID {track_id} : {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Met à jour la table audio_features depuis les JSON Essentia existants.")
    parser.add_argument("--force", action="store_true", help="Force la mise à jour même si les champs existent déjà")
    args = parser.parse_args()
    main(force=args.force)
