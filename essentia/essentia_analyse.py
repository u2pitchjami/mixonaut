from essentia.prep_essentia_analyse import prepare_track_paths, process_audio_file, clean_temp_files, archive_json_result
from utils.config import SCRIPT_PATH_ESSENTIA, PROF_ESSENTIA
from db.essentia_queries import insert_or_update_audio_features
from essentia.essentia_extractions import run_essentia_extraction, parse_essentia_json
from essentia.run_replaygain import run_replaygain_in_container
from essentia.essentia_enrich import enrich_features
from utils.logger import get_logger, with_child_logger
from pathlib import Path

@with_child_logger
def analyse_track(track, force=False, source="Mixonaut", logger=None):
    clean_trigger = False
    try:
        result = prepare_track_paths(track, logger=logger)
        if result is None:
            logger.error(f"❌ Erreur préparation des chemins pour le morceau : {track}")
            return None  # ou log + continue si tu veux tracer
        track_id, original_path, safe_name, temp_audio, temp_json = result
        if not process_audio_file(original_path, temp_audio, logger=logger):
            return None

        profile = Path(PROF_ESSENTIA)
        track_features = extract_and_parse_features(temp_audio, temp_json, profile, logger=logger)
        if not track_features:
            return

        track_features = enrich_features(track_features, logger=logger)

        insert_or_update_audio_features(track_id, track_features, force=force, logger=logger)
        archive_json_result(track_id, safe_name, logger=logger)
        clean_trigger = True
        return track_features

    except Exception as e:
        logger.exception(f"❌ Erreur traitement track {track_id} : {e}")

    finally:
        if clean_trigger:
            logger.debug(f"Nettoyage des fichiers temporaires pour le morceau {track_id}")
            clean_temp_files(temp_audio, temp_json, logger=logger)

@with_child_logger        
def extract_and_parse_features(temp_audio, temp_json, profile, logger=None):
    run_essentia_extraction(
        audio_path=Path(f"/app/music/{temp_audio.name}"),
        json_path=Path(f"/app/music/{temp_json.name}"),
        profile_path=Path(f"/app/profile/{profile.name}"),
        logger=logger
    )
    if not temp_json.exists():
        logger.error(f"JSON non généré pour : {temp_audio}")
        return None
    
    run_replaygain_in_container(audio_path=temp_audio, json_out_path=temp_json, profile_path=profile, logger=logger)
    return parse_essentia_json(temp_json)