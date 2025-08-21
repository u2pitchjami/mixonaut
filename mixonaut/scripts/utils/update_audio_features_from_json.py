"""2025-08-20 - scripts qui regen la table audio_features à partir des json existants."""

import argparse
import os

from mixonaut.db.analyse.essentia_queries import (
    get_all_track_ids,
    insert_or_update_audio_features,
)
from mixonaut.essentia.analyse.essentia_extractions import parse_essentia_json
from mixonaut.utils.config import ESSENTIA_SAV_JSON
from mixonaut.utils.logger import get_logger
from mixonaut.utils.safe_runner import safe_main

logger = get_logger("Update_Features_From_JSON")


@safe_main
def main(force=False):
    """
    Main function to update audio features from existing JSON files.

    This function retrieves all track IDs, generates the necessary paths for each track,
    parses the corresponding JSON file using Essentia, and inserts or updates the audio features in the database.

    Args:
        force (bool): Flag indicating whether to overwrite existing data in the database. Defaults to False.
    """
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

        json_file = next(
            (
                f
                for f in os.listdir(subdir)
                if f.startswith(f"{track_id}_") and f.endswith(".json")
            ),
            None,
        )
        if not json_file:
            logger.warning(
                f"Fichier JSON non trouvé pour track ID {track_id} dans {subdir}"
            )
            continue

        json_path = os.path.join(subdir, json_file)

        result = parse_essentia_json(json_path, logger=logger)
        if not result:
            continue
        insert_or_update_audio_features(track_id, result, force=force, logger=logger)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Met à jour la table audio_features depuis les JSON Essentia existants."
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force la mise à jour même si les champs existent déjà",
    )
    args = parser.parse_args()
    main(force=args.force)
