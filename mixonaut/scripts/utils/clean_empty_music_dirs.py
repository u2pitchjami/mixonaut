"""2025-08-20 - script qui supprime les dossiers vides."""

import argparse
import os
import shutil
from datetime import datetime

from mixonaut.utils.config import AUDIO_EXTENSIONS, IGNORED_EXTENSIONS, MUSIC_BASE_PATH
from mixonaut.utils.logger import get_logger
from mixonaut.utils.safe_runner import safe_main

logger = get_logger("Clean_Empty_Music_Dirs")


# --- Fonctions utilitaires ---
def is_audio_file(filename: str) -> bool:
    """
    Checks if a given filename has an audio file extension.

    Args:
        filename (str): The name of the file to check.

    Returns:
        bool: True if the file has an audio file extension, False otherwise.
    """
    return os.path.splitext(filename)[1].lower() in AUDIO_EXTENSIONS


def is_ignored_file(filename: str) -> bool:
    """
    Docstring for is_ignored_file function:

    This function checks if a given filename contains an extension that should be ignored.

    Parameters:
    filename (str): The name of the file to check.

    Returns:
    bool: True if the file has an ignored extension, False otherwise.
    """
    return os.path.splitext(filename)[1].lower() in IGNORED_EXTENSIONS


def should_delete_folder(folder_path: str) -> bool:
    """
    Determines whether a folder should be deleted if it contains at least one non-empty, non-ignored audio file.

    Args:
        folder_path (str): The path to the folder to check.

    Returns:
        bool: True if the folder is empty after filtering out ignored and non-audio files, False otherwise.
    """
    for _, _, files in os.walk(folder_path):
        for file in files:
            if is_audio_file(file):
                return False
            if not is_ignored_file(file):
                return False
    return True


# --- Fonction principale ---
@safe_main
def clean_music_collection(base_path: str, delete: bool = False) -> None:
    """
    Clean up the music collection by removing empty folders and those without audio files.

    Args:
        base_path (str): The path to start cleaning from.
        delete (bool): Whether to actually delete the removed folders. Defaults to False.

    Returns:
        None
    """
    total_checked = 0
    marked_for_deletion = 0
    deleted_count = 0
    failed_deletions = 0

    logger.info(f"📅 CLEAN COLLECTION : {datetime.now().strftime('%d-%m-%Y')}")
    logger.info("--- (supprime les dossiers vides ou sans fichiers musicaux) ---")

    for root, dirs, files in os.walk(base_path, topdown=False):
        total_checked += 1
        if should_delete_folder(root):
            marked_for_deletion += 1
            if delete:
                try:
                    # os.rmdir(root)
                    shutil.rmtree(root)
                    logger.info(f"[SUPPRIMÉ] {root}")
                    deleted_count += 1
                except OSError as e:
                    logger.warning(f"[ÉCHEC] {root} : {e}")
                    failed_deletions += 1
            else:
                logger.info(f"[À supprimer] {root}")

    logger.info("📢 --- Résumé ---")
    logger.info(f"🔍 Dossiers analysés     : {total_checked}")
    logger.info(f"💊 Dossiers à supprimer  : {marked_for_deletion}")
    logger.info(f"☀️ Dossiers supprimés    : {deleted_count}")
    logger.info(f"🚨 Échecs de suppression : {failed_deletions}")

    logger.info("🏁 CLEAN COLLECTION : TERMINE !! \n\n")


# --- Entrée script ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Nettoie les dossiers vides ou sans musiques."
    )
    parser.add_argument(
        "--delete",
        action="store_true",
        default=True,
        help="Supprime réellement les dossiers",
    )
    parser.add_argument(
        "--path", default=MUSIC_BASE_PATH, help="Chemin de base à scanner"
    )
    args = parser.parse_args()

    clean_music_collection(args.path, delete=args.delete)
