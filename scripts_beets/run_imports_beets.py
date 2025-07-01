import os
import shutil
import time
import tempfile
import subprocess
import argparse
from utils.utils_div import format_nb, format_percent
from utils.config import MUSIC_SOURCE_PATH, MUSIC_IMPORT_PATH
from beets_utils.imports import import_auto
from db.import_queries import (
    is_already_imported,
    insert_or_update_imported,
    cleanup_missing_imported
)
from utils.logger import get_logger, with_child_logger

logger = get_logger("Run_Imports_Beets")

@with_child_logger
def scan_and_process_downloads(source_dir: str = MUSIC_SOURCE_PATH, import_dir: str = MUSIC_IMPORT_PATH, logger=None):
    logger.info(f"🔍 Début du scan des téléchargements dans : {source_dir} and import dans : {import_dir}")
    try:
        files = os.listdir(source_dir)
        logger.debug(f"Liste des fichiers trouvés: {files}")
        logger.info(f"Nombre d'éléments dans le dossier downloads: {len(files)}")
    except FileNotFoundError:
        logger.error(f"Le dossier source {source_dir} n'existe pas.")
        return
    except PermissionError:
        logger.error(f"Permission refusée pour accéder au dossier {source_dir}.")
        return
    except Exception:
        logger.exception("Erreur inattendue lors de la lecture du dossier source.")
        return

    count = 0
    for root, dirs, files in os.walk(source_dir):
        for name in files:
            count += 1
            try:
                logger.info(f"▶️  Traitement de l'élément :: {name} - [{format_nb(count, logger=logger)}/{format_nb(len(files), logger=logger)}] ({format_percent(count, len(files), logger=logger)})")
                path = os.path.join(root, name)
                size = os.path.getsize(path)

                if is_already_imported(path, size, logger=logger):
                    logger.info(f"Déjà importé : {path}")
                    continue

                # Extraction selon l'extension
                if name.lower().endswith(('.zip', '.tar', '.tar.gz', '.tar.bz2')):
                    with tempfile.TemporaryDirectory() as tmpdir:
                        shutil.unpack_archive(path, tmpdir)
                        _copy_tree(tmpdir, import_dir, logger=logger)
                        logger.info(f"Archive extraite et copiée : {path}")

                elif name.lower().endswith('.rar'):
                    with tempfile.TemporaryDirectory() as tmpdir:
                        subprocess.run(['unrar', 'x', '-y', path, tmpdir], check=True)
                        _copy_tree(tmpdir, import_dir, logger=logger)
                        logger.info(f"Archive RAR extraite et copiée : {path}")

                elif name.lower().endswith('.7z'):
                    with tempfile.TemporaryDirectory() as tmpdir:
                        subprocess.run(['7z', 'x', '-y', f'-o{tmpdir}', path], check=True)
                        _copy_tree(tmpdir, import_dir, logger=logger)
                        logger.info(f"Archive 7z extraite et copiée : {path}")

                else:
                    rel_path = os.path.relpath(path, source_dir)
                    parts = rel_path.split(os.sep)
                    if len(parts) == 1:
                        dest = os.path.join(import_dir, 'singles', name)
                    else:
                        dest = os.path.join(import_dir, rel_path)

                    os.makedirs(os.path.dirname(dest), exist_ok=True)
                    shutil.copy2(path, dest)
                    logger.info(f"Éléments copiés : {path} → {dest}")

                insert_or_update_imported(path, size, logger=logger)

            except subprocess.CalledProcessError as e:
                logger.error(f"Erreur lors de l'extraction de {name} : {e}")
            except Exception:
                logger.exception(f"Erreur inattendue lors du traitement de {name}")

    cleanup_missing_imported(logger=logger)
    logger.info("🔍 Fin du scan et traitement des téléchargements")


@with_child_logger
def _copy_tree(src_dir, dest_dir, logger=None):
    for root, dirs, files in os.walk(src_dir):
        for name in files:
            rel_path = os.path.relpath(os.path.join(root, name), src_dir)
            dest = os.path.join(dest_dir, rel_path)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copy2(os.path.join(root, name), dest)


if __name__ == "__main__":
    try:
        parser = argparse.ArgumentParser()
        parser.add_argument("--source-dir", type=str)
        parser.add_argument("--import-dir", type=str)       
        args = parser.parse_args()
        scan_and_process_downloads(logger=logger)
        logger.info("🔍 Fin du Scan - Démarrage de l'import Beets")
        import_auto(logger=logger)
        logger.info("🏁 Traitement Essentia_recalc terminé")
    except Exception as e:
        logger.error(f"Erreur lors de l'exécution du script : {e}")