import subprocess
import argparse
import random
from utils.config import RETRO_MIXONAUT_BEETS, MUSIC_BASE_PATH, BEETS_MUSIC, IMAGE_BEETS
from utils.utils_div import format_nb, format_percent
from db.access import select_all, execute_query
from db.essentia_queries import get_all_track_ids, get_audio_features_by_id
from db.db_beets_queries import get_item_field_value
from logic.write_tags import write_tags_docker, docker_metaflac_cmd
from logic.sync_beets_from_essentia import build_sync_fields
from utils.utils_div import ensure_to_str, convert_path_format
from utils.logger import get_logger
import os

logname = "Check_&_fix_tags"
logger = get_logger(logname)

def get_current_tags(path: str) -> dict:
    tags = {}
    try:
        ext = os.path.splitext(path)[1].lower()
        container_path = path.replace(MUSIC_BASE_PATH, BEETS_MUSIC)

        if ext == ".mp3":
            for tag in RETRO_MIXONAUT_BEETS:
                cmd = [
                    "docker", "run", "--rm",
                    "-v", f"{MUSIC_BASE_PATH}:{BEETS_MUSIC}",
                    IMAGE_BEETS,
                    "bash", "-c",
                    f"eyeD3 --no-color '{container_path}'"
                ]
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode == 0:
                    for line in result.stdout.splitlines():
                        for t in RETRO_MIXONAUT_BEETS:
                            if f"{t}:" in line:
                                value = line.split(f"{t}:", 1)[1].strip()
                                tags[t] = value

        elif ext == ".flac":
            for tag in RETRO_MIXONAUT_BEETS:
                tag_upper = tag.upper()
                result = subprocess.run(
                    docker_metaflac_cmd(container_path, ["--show-tag=" + tag_upper]),
                    capture_output=True,
                    text=True,
                    check=False
                )
                if result.stdout.strip():
                    tags[tag] = result.stdout.strip().split("=", 1)[-1]

    except Exception as e:
        logger.warning(f"Erreur lors de la lecture des tags pour {path}: {e}")
    return tags

def check_and_fix_tags(track_id: int, path: str, track_features: dict, dry_run: bool = False) -> bool:
    
    expected_tags = build_sync_fields(track_id, track_features, logname=logname)
    logger.debug(f"expected_tags : {expected_tags}")
    current_tags = get_current_tags(path)
    logger.debug(f"current_tags : {current_tags}")
    diffs = {}

    for key in RETRO_MIXONAUT_BEETS:
        expected_value = str(expected_tags.get(key, ""))
        current_value = str(current_tags.get(key, ""))
        if expected_value and expected_value != current_value:
            diffs[key] = {"current": current_value, "expected": expected_value}

    if diffs:
        tags_to_update = {key: val["expected"] for key, val in diffs.items()}
        logger.debug(f"tags_to_update {tags_to_update}")
        logger.info(f"⚡ Écarts détectés pour {track_id}: {diffs}")
        new_path = convert_path_format(path=path, to_beets=False)
        if not dry_run:
            try:
                write_tags_docker(new_path, tags_to_update)
                logger.info(f"👌 Tags mis à jour pour {track_id}")
            except Exception as e:
                logger.error(f"Erreur lors de l’écriture des tags pour {path}: {e}")
        return True

    return False

def process_all_tracks(dry_run: bool = False, track_id: int = None, nb_limit: int = 0):
    args_to_log = {k: v for k, v in locals().items() if k != "track_ids"}

    track_ids = get_all_track_ids()
    if track_id:
        if track_id in track_ids:
            track_ids = [track_id]  # ← transforme en liste d’un seul élément            
        else:
            raise ValueError(f"Track ID {track_id} non trouvé dans la base.")
    total = nb_limit
    if nb_limit == 0:
        nb_limit = len(track_ids)
        total = len(track_ids)
    random.shuffle(track_ids)
    track_ids = track_ids[:nb_limit]
    
         
    logger.info(f"Démarrage de la vérification des tags pour {format_nb(total)} pistes (dry_run={dry_run})")
    logger.info("Arguments reçus : " + ", ".join([f"{k}={v}" for k, v in args_to_log.items()]))
    updated = 0
    count = 0

    for i, track_id in enumerate(track_ids, 1):
        count += 1
        if updated >= 1:
            logger.info(f"▶️  Analyse : {track_id} - [{format_nb(count)}/{format_nb(total)}] ({format_percent(count, total)}) - {format_nb(updated)} updated ({format_percent(updated, total)})")
        else:
            logger.info(f"▶️  Analyse : {track_id} - [{format_nb(count)}/{format_nb(total)}] ({format_percent(count, total)})")
        features = get_audio_features_by_id(track_id)
        if not features:
            continue

        path = get_item_field_value("path", track_id)
        path = ensure_to_str(path)
        if not path:
            logger.warning(f"Fichier introuvable pour l'ID {track_id}: {path}")
            continue

        if check_and_fix_tags(track_id, path, features, dry_run=dry_run):
            updated += 1
        

    logger.info(f"🏁 Terminé. {updated} fichiers avec tags modifiés (ou à modifier en dry_run)")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--track-id", type=int, required=False)
    parser.add_argument("--dry-run", action="store_true", help="Mode Dry")
    parser.add_argument("--nb-limit", type=int, default=0, help="Nombre d'éléments à traiter (défaut: 0)")
    args = parser.parse_args()
    process_all_tracks(dry_run=args.dry_run, track_id=args.track_id, nb_limit=args.nb_limit)
