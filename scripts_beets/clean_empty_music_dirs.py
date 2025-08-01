import os
import argparse
from datetime import datetime
from utils.config import MUSIC_BASE_PATH, AUDIO_EXTENSIONS, IGNORED_EXTENSIONS
import shutil
from utils.safe_runner import safe_main
from utils.logger import get_logger

logger = get_logger("Clean_Empty_Music_Dirs")

# --- Fonctions utilitaires ---
def is_audio_file(filename: str) -> bool:
    return os.path.splitext(filename)[1].lower() in AUDIO_EXTENSIONS

def is_ignored_file(filename: str) -> bool:
    return os.path.splitext(filename)[1].lower() in IGNORED_EXTENSIONS

def should_delete_folder(folder_path: str) -> bool:
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
                    #os.rmdir(root)
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
    
    logger.info(f"🏁 CLEAN COLLECTION : TERMINE !! \n\n")

# --- Entrée script ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Nettoie les dossiers vides ou sans musiques.")
    parser.add_argument("--delete", action="store_true", default=False, help="Supprime réellement les dossiers")
    parser.add_argument("--path", default=MUSIC_BASE_PATH, help="Chemin de base à scanner")
    args = parser.parse_args()

    clean_music_collection(args.path, delete=args.delete)