import os
import shutil
import subprocess
import uuid
import json
import traceback
import unicodedata
import re
from pathlib import Path
from logic.run_replaygain import run_replaygain_in_container
from utils.config import ESSENTIA_TEMP_AUDIO, ESSENTIA_TEMP_JSON, SCRIPT_PATH_ESSENTIA,SCRIPT_PATH_REPLAYGAIN, PROF_ESSENTIA, ESSENTIA_SAV_JSON
from logic.essentia import run_essentia_extraction, parse_essentia_json, get_best_key_from_essentia
from logic.essentia_calculate import calculate_beat_intensity, compute_energy_level, extract_essentia_genres, get_dominant_mood,compute_mood_vector, convert_to_camelot
from utils.logger import get_logger
from scripts_beets.check_retro_beets import sync_beets_from_mixonaut
from db.essentia_queries import fetch_tracks_missing_essentia, insert_or_update_audio_features
from db.db_utils import update_tracks_meta
from utils.utils_div import ensure_to_path, convert_path_format, sanitize_value

logname = "Essentia_Tags"
logger = get_logger(logname)

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
    try:
        track_id, raw_path, artist, album, title, beet_id = track
    
        logger.debug(f"raw_path : {type(raw_path)}")
        path_str = ensure_to_path(raw_path)
        logger.debug(f" path_str : {type(path_str)}")
        path_norma = convert_path_format(path=path_str, to_beets=False)
        path = Path(path_norma)
        logger.debug(f"path : {type(path)}")
    except Exception as e:
        logger.error(f"❌ [{__name__.split(".")[-1]}] Erreur dans les paths {track_id} : {e}")
        raise
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
            return False
                
        run_essentia_extraction(
        audio_path=Path(f"/app/music/{temp_audio.name}"),
        json_path=Path(f"/app/music/{temp_json.name}"),
        profile_path=Path(f"/app/profile/{PROFILE_ESSENTIA.name}"),
        logname=logname
        )

        if not temp_json.exists():
            logger.error(f"JSON non généré pour : {path}")
            return

        run_replaygain_in_container(audio_path=temp_audio, json_out_path=temp_json)

        track_features = parse_essentia_json(temp_json)
        track_features["bpm_essentia"] = sanitize_value(track_features.get("bpm_essentia"), "bpm")
        track_features["rg_gain"] = sanitize_value(track_features.get("rg_gain"), "rg_gain")
        
        
        
        logger.debug(f"features extraits : {track_features}")
        if source == "Mixonaut":
            insert_or_update_audio_features(track_id=track_id, features=track_features, force=force, logname=logname)
            
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
        
        best_key_data = get_best_key_from_essentia(track_features=track_features)
        logger.debug(f" best_key_data : {best_key_data}")
        if best_key_data:
            camelot = convert_to_camelot(best_key_data["key"], best_key_data["scale"])
            logger.debug(f" camelot : {camelot}")
            track_features["camelot_key"] = camelot
            track_features["camelot_key"] = sanitize_value(track_features.get("camelot_key"), "key")
            logger.debug(f" camelot_key : {track_features["camelot_key"]}")
            track_features["key_strength"] = best_key_data["strength"]

        
        if source == "Mixonaut":
            archive_json_result(track_id=track[0], safe_name=safe_name)
        
        return track_features

    except Exception as e:
        logger.exception(f"❌ [{__name__.split(".")[-1]}] Erreur traitement track {track_id} : {e}")
    # finally:
    #     if temp_audio.exists():
    #         temp_audio.unlink()
    #     if temp_json.exists():
    #         temp_json.unlink()

def main(force=False, count=0):
    logger.info("🔍 Démarrage analyse des morceaux via Essentia")
    try:
        tracks = fetch_tracks_missing_essentia(force=force)
        logger.info(f"🎯 {len(tracks)} morceaux à analyser")
        if not tracks:
            logger.info("Aucun morceau à traiter")
            return
        
        for track in tracks[:count]:
            track_features = analyse_track(track, force=force, source="Mixonaut")
            update_tracks_meta(track_id=track[0], energy_level=track_features["energy_level"], beat_intensity=track_features["beat_intensity"], mood=track_features["mood"], essentia_genres=track_features["essentia_genres"], key=track_features["camelot_key"], bpm=track_features["bpm_essentia"], rg_gain=track_features["rg_gain"], force=True, logname="Essentia_Tags")
            logger.info(f"✅ Track mis à jour : {track[0]}")
            print(f"Track ID: {track[0]}, Path: {track[1]}, Artist: {track[2]}, Album: {track[3]}, Title: {track[4]}, Beet ID: {track[5]}")
            sync_beets_from_mixonaut(
                beet_id=track[5],
                path=track[1],
                artist=track[2],
                album=track[3],
                title=track[4],
                mb_trackid=None
            )
            track_id, raw_path, artist, album, title, beet_id = track
        logger.info("🏁 Traitement terminé")
    except Exception as e:
        raise

if __name__ == "__main__":
    import argparse
    try:
        parser = argparse.ArgumentParser()
        parser.add_argument("--force", action="store_true", help="Forcer le recalcul même si les champs sont déjà remplis")
        parser.add_argument("--count", type=int, default=0, help="Nombre d'éléments à traiter (défaut: 0)")
        
        args = parser.parse_args()
        main(force=args.force, count=args.count)
    except Exception as e:
        raise SystemExit(1)