from essentia.prep_essentia_analyse import prepare_track_paths, process_audio_file, clean_temp_files, archive_json_result
from utils.config import SCRIPT_PATH_ESSENTIA, PROF_ESSENTIA
from db.essentia_queries import insert_or_update_audio_features
from essentia.essentia_extractions import run_essentia_extraction, parse_essentia_json
from essentia.run_replaygain import run_replaygain_in_container
from essentia.essentia_enrich import enrich_features
from utils.logger import get_logger
from pathlib import Path

logname = __name__.split(".")[-1]

def analyse_track(track, force=False, source="Mixonaut", logname=logname):
    logger = get_logger(logname)
    logger.debug(f"SCRIPT_PATH_ESSENTIA : {SCRIPT_PATH_ESSENTIA}")
    logger.debug(f"ESSENTIA_PROFILE : {PROF_ESSENTIA}")
    clean_trigger = False

    try:
        result = prepare_track_paths(track, logname=logname)
        if result is None:
            logger.error(f"❌ Erreur préparation des chemins pour le morceau : {track}")
            return None  # ou log + continue si tu veux tracer
        track_id, original_path, safe_name, temp_audio, temp_json = result
        if not process_audio_file(original_path, temp_audio, logname=logname):
            return None

        profile = Path(PROF_ESSENTIA)
        track_features = extract_and_parse_features(temp_audio, temp_json, profile, logname=logname)
        if not track_features:
            return

        track_features = enrich_features(track_features, logname=logname)

        insert_or_update_audio_features(track_id, track_features, force=force, logname=logname)
        archive_json_result(track_id, safe_name, logname=logname)
        clean_trigger = True
        return track_features

    except Exception as e:
        logger.exception(f"❌ Erreur traitement track {track_id} : {e}")

    finally:
        if clean_trigger:
            logger.debug(f"Nettoyage des fichiers temporaires pour le morceau {track_id}")
            clean_temp_files(temp_audio, temp_json, logname=logname)
        
def extract_and_parse_features(temp_audio, temp_json, profile, logname=logname):
    logger = get_logger(logname)
    run_essentia_extraction(
        audio_path=Path(f"/app/music/{temp_audio.name}"),
        json_path=Path(f"/app/music/{temp_json.name}"),
        profile_path=Path(f"/app/profile/{profile.name}"),
        logname=logname
    )
    if not temp_json.exists():
        logger.error(f"JSON non généré pour : {temp_audio}")
        return None

    run_replaygain_in_container(audio_path=temp_audio, json_out_path=temp_json, profile_path=profile, logname=logname)
    return parse_essentia_json(temp_json)