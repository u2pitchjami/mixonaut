import os
import shutil
import subprocess
import uuid
import json
import traceback
import unicodedata
import re
from pathlib import Path
from utils.config import ESSENTIA_TEMP_AUDIO, ESSENTIA_TEMP_JSON, SCRIPT_PATH_ESSENTIA, PROF_ESSENTIA, ESSENTIA_SAV_JSON
from logic.essentia import run_essentia_extraction, parse_essentia_json
from logic.essentia_calculate import calculate_beat_intensity, compute_energy_level, extract_essentia_genres, get_dominant_mood,compute_mood_vector 
from utils.logger import get_logger
from db.essentia_queries import fetch_tracks_missing_essentia, insert_or_update_audio_features
from db.db_utils import update_tracks_meta
from utils.utils_div import ensure_to_path, convert_path_format

logger = get_logger("Essentia_Tags")

def sanitize_filename(name: str) -> str:
    # Enlève les accents
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    # Garde uniquement lettres, chiffres, tirets, underscores
    name = re.sub(r"[^\w\-]", "_", name)
    # Remplace multiples underscores par un seul
    name = re.sub(r"__+", "_", name)
    return name.strip("_").lower()

def archive_json_result(track_id: int, safe_name: str):
    """
    Déplace un JSON de `temp_folder` vers `archive_base/XXXX/` en fonction de track_id
    """
   
    # Dossier de destination
    target_folder = Path(ESSENTIA_SAV_JSON) / f"{(track_id // 1000) * 1000:04d}"
    target_folder.mkdir(parents=True, exist_ok=True)

    # Fichier source et destination
    source = Path(ESSENTIA_TEMP_JSON) / f"{safe_name}.json"
    dest = target_folder / f"{safe_name}.json"

    if not source.exists():
        logger.warning(f"❌ JSON temporaire non trouvé pour track {track_id} : {source}")
        return

    try:
        shutil.copy(source, dest)
        logger.debug(f"✅ JSON archivé : {dest}")
    except Exception as e:
        logger.warning(f"Erreur archivage JSON {track_id} : {e}")


def analyse_track(track, force=False, source="Mixonaut"):
    logger.debug(f"SCRIPT_PATH_ESSENTIA : {SCRIPT_PATH_ESSENTIA}")
    logger.debug(f"ESSENTIA_PROFILE : {PROF_ESSENTIA}")
    print(f"track : {type(track)}")
    track_id, raw_path, artist, album, title, beet_id = track
   
    logger.debug(f"raw_path : {type(raw_path)}")
    path_str = ensure_to_path(raw_path)
    logger.debug(f" path_str : {type(path_str)}")
    path_norma = convert_path_format(path=path_str, to_beets=False)
    path = Path(path_norma)
    logger.debug(f"path : {type(path)}")
    try:
        original_path = Path(path)
        if not original_path.exists():
            logger.warning(f"Fichier introuvable : {path}")
            return
        safe_name = f"{track_id}_{beet_id}_{sanitize_filename(artist)}_{sanitize_filename(album)}_{sanitize_filename(title)}"
        logger.debug(f"safe_name : {safe_name}")
        temp_audio = Path(ESSENTIA_TEMP_AUDIO) / f"{safe_name}{original_path.suffix}"
        logger.debug(f"temp_audio.name : {temp_audio.name}")
        temp_json = Path(ESSENTIA_TEMP_JSON) / f"{safe_name}.json"
        logger.debug(f"temp_json : {temp_json}")
        logger.debug(f"original_path : {original_path}")
        logger.debug(f"temp_audio : {temp_audio}")
        PROFILE_ESSENTIA = Path(PROF_ESSENTIA)
        
        try:
            shutil.copy(original_path, temp_audio)
        except Exception as e:
            logger.error(f"Erreur lors de la copie du fichier : {path}")
            logger.debug(traceback.format_exc())
            return False
                
        run_essentia_extraction(
        audio_path=Path(f"/app/music/{temp_audio.name}"),
        json_path=Path(f"/app/music/{temp_json.name}"),
        profile_path=Path(f"/app/profile/{PROFILE_ESSENTIA.name}"),
        logname="Essentia_Tags"
        )

        if not temp_json.exists():
            logger.error(f"JSON non généré pour : {path}")
            return

        track_features = parse_essentia_json(temp_json)
        logger.debug(f"features extraits : {track_features}")
        if source == "Mixonaut":
            insert_or_update_audio_features(track_id=track_id, features=track_features, force=force, logname="Essentia_Tags")
            
        track_features["beat_intensity"] = calculate_beat_intensity(track_features, logname="Essentia_Tags")
        logger.debug(f"beat_intensity : {track_features["beat_intensity"]}")
        track_features["energy_level"] = compute_energy_level(track_features, logname="Essentia_Tags")
        logger.debug(f"energy_level : {track_features["energy_level"]}")
        track_features["mood_vector"] = compute_mood_vector(features=track_features,  logname="Essentia_Tags")
        logger.debug(f"mood_vector : {track_features["mood_vector"]}")
        track_features["mood"] = get_dominant_mood(mood_vector=track_features["mood_vector"])
        logger.debug(f"mood : {track_features["mood"]}")
        track_features["essentia_genres"] = extract_essentia_genres(features=track_features, logname="Mix_Assist")
        logger.debug(f"essentia_genres : {track_features["essentia_genres"]}")
        
        if source == "Mixonaut":
            archive_json_result(track_id=track[0], safe_name=safe_name)
        
        return track_features

    except Exception as e:
        logger.exception(f"Erreur traitement track {track_id} : {e}")
    # finally:
    #     if temp_audio.exists():
    #         temp_audio.unlink()
    #     if temp_json.exists():
    #         temp_json.unlink()

def main(force=False, count=0):
    logger.info("🔍 Démarrage analyse des morceaux via Essentia")
    tracks = fetch_tracks_missing_essentia(force=force)

    logger.info(f"🎯 {len(tracks)} morceaux à analyser")
    for track in tracks[:count]:
        track_features = analyse_track(track, force=force, source="Mixonaut")
        print(f"track_features : {track_features}")
        update_tracks_meta(track_id=track[0], energy_level=track_features["energy_level"], beat_intensity=track_features["beat_intensity"], mood=track_features["mood"], essentia_genres=track_features["essentia_genres"], force=True, logname="Essentia_Tags")
        logger.info(f"✅ Track mis à jour : {track[0]}")
        
    logger.info("🏁 Traitement terminé")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="Forcer le recalcul même si les champs sont déjà remplis")
    parser.add_argument("--count", type=int, default=0, help="Nombre d'éléments à traiter (défaut: 0)")
    
    args = parser.parse_args()
    main(force=args.force, count=args.count)
