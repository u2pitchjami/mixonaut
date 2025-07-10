import os
import shutil
import tempfile
import subprocess
from pathlib import Path
from datetime import datetime
from logic_imports.process_archives import handle_archive
from logic_imports.imports_utils import extract_torrent_name
from utils.utils_div import format_nb, format_percent
from logic_imports.extract_cue import split_cue_and_convert_ffmpeg
from utils.config import MUSIC_SOURCE_PATH, MUSIC_IMPORT_PATH, MUSIC_IMPORT_TEMP_PATH
from beets_utils.imports import import_auto
from db.import_queries import (
    is_already_imported,
    insert_or_update_imported,
    cleanup_missing_imported
)
from utils.logger import get_logger, with_child_logger

@with_child_logger
def scan_and_process_downloads(source_dir: str = MUSIC_SOURCE_PATH, import_dir: str = MUSIC_IMPORT_PATH, import_temp_dir: str = MUSIC_IMPORT_TEMP_PATH, nb_limit=0, logger=None):
    logger.info(f"🔍 Début du scan des téléchargements dans : {source_dir} and import dans : {import_dir}")
    try:
        entries = os.listdir(source_dir)[:nb_limit]
        logger.info(f"Nombre d'éléments dans le dossier downloads: {len(entries)}")
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
    cue_trigger = False
    cue_temp_dirs = []
    processed_dirs = set()

    for root, dirs, files in os.walk(source_dir):
        logger.debug(f"Exploration du dossier : {root}, avec {dirs} sous-dossiers et {files} fichiers")               
        for name in files:
            count += 1
            try:
                logger.info(f"▶️  Traitement de l'élément :: {name} - [{format_nb(count, logger=logger)}/{format_nb(len(files), logger=logger)}] ({format_percent(count, len(files), logger=logger)})")
                
                path = os.path.join(root, name)
                size = os.path.getsize(path)
                logger.debug(f"Chemin complet : {path}, Taille : {size} octets")
                torrent_name = extract_torrent_name(import_path = path, base_path = source_dir, logger=logger)
                logger.debug(f"Nom du torrent extrait : {torrent_name}")

                if is_already_imported(name=name, torrent_name=torrent_name, logger=logger):
                    logger.info(f"Déjà importé : {name} dans {torrent_name}, passage au suivant.")
                    continue

                # Extraction (si archive)
                if name.lower().endswith(('.zip', '.tar', '.tar.gz', '.tar.bz2', '.rar', '.7z')):
                    handle_archive(path, import_dir, logger=logger)

                # Traitement des .cue
                elif name.lower().endswith('.cue'):
                    cue_trigger = True
                    converted_dir = split_cue_and_convert_ffmpeg(path, logger=logger)
                    if converted_dir:
                        cue_temp_dirs.append(converted_dir)
                        for croot, cdirs, cfiles in os.walk(converted_dir):
                            for cf in cfiles:
                                src_file = os.path.join(croot, cf)
                                rel_path = os.path.relpath(root, source_dir)
                                dest_file = os.path.join(import_dir, rel_path, cf)
                                os.makedirs(os.path.dirname(dest_file), exist_ok=True)
                                shutil.copy2(src_file, dest_file)
                        logger.info(f"Pistes splittées et converties copiées dans {import_dir}")

                # Cas générique : copie normale
                else:
                    rel_path = os.path.relpath(path, source_dir)
                    parts = rel_path.split(os.sep)
                    if len(parts) == 1:
                        # 🔤 Nettoyage du nom du fichier pour créer un nom de dossier safe
                        base_name = os.path.splitext(name)[0]
                        safe_name = base_name.replace(" ", "_").replace("/", "_")
                        date_prefix = datetime.now().strftime("%Y%m%d")
                        folder_name = f"{date_prefix}_{safe_name}"

                        # 📁 Création d’un dossier dédié dans le dossier d’import
                        #solo_source_dir = os.path.join(import_dir, folder_name)
                        #logger.debug(f"Création du dossier solo : {solo_source_dir}")
                        solo_dest_dir = os.path.join(import_dir, folder_name)
                        logger.debug(f"Création du dossier de destination solo : {solo_dest_dir}")
                        #source = os.path.join(solo_dest_dir, name)
                        #logger.debug(f"Source pour copie : {source}")
                        dest = os.path.join(solo_dest_dir, name)
                        logger.debug(f"Destination pour copie : {dest}")
                        os.makedirs(os.path.dirname(dest), exist_ok=True)
                        shutil.copy2(path, dest)
                        #_copy_tree(solo_source_dir, import_dir, logger=logger)
                        # 📌 Enregistrement dans la base avec le dossier source simulé
                        #source_folder = os.path.join(source_dir, folder_name)
                    else:
                        dest = os.path.join(import_dir, rel_path)

                    if cue_trigger and name.lower().endswith(('.flac', '.wav', '.ape', '.wv', '.mp3')):
                        logger.info(f"Éléments copiés : {path} → {dest}")
                    else:
                        os.makedirs(os.path.dirname(dest), exist_ok=True)
                        shutil.copy2(path, dest)
                        logger.info(f"Éléments copiés : {path} → {dest}")

                #insert_or_update_imported(path, size, logger=logger)

            except subprocess.CalledProcessError as e:
                logger.error(f"Erreur lors de l'extraction de {name} : {e}")
            except Exception:
                logger.exception(f"Erreur inattendue lors du traitement de {name}")

    #cleanup_missing_imported(logger=logger)
    logger.info("🔍 Fin du scan et traitement des téléchargements")
