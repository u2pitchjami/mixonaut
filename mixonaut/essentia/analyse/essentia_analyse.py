from __future__ import annotations
from essentia.analyse.prep_essentia_analyse import prepare_track_paths, process_audio_file, clean_temp_files, archive_json_result
from db.analyse.essentia_queries import insert_or_update_audio_features
from essentia.analyse.essentia_extractions import run_essentia_extraction, parse_essentia_json
from essentia.features.run_replaygain import run_replaygain_in_container
from essentia.features.essentia_enrich import enrich_features
from utils.config import PROF_ESSENTIA
from utils.logger import with_child_logger
from pathlib import Path
from typing import Any, Dict, Optional

@with_child_logger
def analyse_track_wo_essentia(
    json_path: str | Path,
    track_id: int,
    force: bool = False,
    logger=None
) -> Optional[Dict[str, Any]]:
    """
    Charge un JSON Essentia déjà produit, calcule les features dérivées
    et met à jour la base. Ne lance PAS docker/Essentia.

    Returns:
        dict des features si OK, sinon None.
    """
    try:
        path = Path(json_path)
        if not path.exists():
            logger.warning(f"❌ JSON introuvable pour track {track_id}: {path}")
            return None, "KO_FILE", f"JSON introuvable : {path}"

        track_features = parse_essentia_json(path, logger=logger)
        if not track_features:
            logger.warning(f"❌ Aucune caractéristique extraite (track {track_id})")
            return None, "KO_AUDIO", "JSON vide ou invalide"

        # Enrichissements (BPM arrondi, key/scale normalisés, etc.)
        track_features = enrich_features(track_features, logger=logger)

        insert_or_update_audio_features(track_id, track_features, force=force, logger=logger)
        return track_features, None, None

    except Exception as exc:  # pylint: disable=broad-except
        logger.exception(f"❌ Erreur traitement track {track_id}: {exc}")
        return None, "KO_FILE", str(exc)
    

@with_child_logger
def analyse_track(track, force=False, source="Mixonaut", logger=None):
    clean_trigger = False
    try:
        result = prepare_track_paths(track, logger=logger)
        if result is None:
            logger.error(f"❌ Erreur préparation des chemins pour le morceau : {track}")
            return None, "KO_FILE", "Erreur préparation chemins"
        track_id, original_path, safe_name, temp_audio, temp_json = result
        if not process_audio_file(original_path, temp_audio, logger=logger):
            return None, "KO_FILE", "Erreur préparation fichier audio"

        profile = Path(PROF_ESSENTIA)
        track_features, error_code, error_message = extract_and_parse_features(temp_audio, temp_json, profile, logger=logger)
        if not track_features:
            logger.warning(f"❌ Erreur traitement track {track_id} : Aucune caractéristique extraite")
            return None, "KO_AUDIO", error_message or "JSON vide ou invalide"

        track_features = enrich_features(track_features, logger=logger)

        insert_or_update_audio_features(track_id, track_features, force=force, logger=logger)
        archive_json_result(track_id, safe_name, logger=logger)
        clean_trigger = True
        return track_features, None, None

    except Exception as e:
        logger.exception(f"❌ Erreur traitement track {track_id} : {e}")
        return None, "KO_FILE", str(e)

    finally:
        if clean_trigger:
            logger.debug(f"Nettoyage des fichiers temporaires pour le morceau {track_id}")
            clean_temp_files(temp_audio, temp_json, logger=logger)

@with_child_logger        
def extract_and_parse_features(temp_audio, temp_json, profile, logger=None):
    error_code, error_message = run_essentia_extraction(
        audio_path=Path(f"/app/music/{temp_audio.name}"),
        json_path=Path(f"/app/music/{temp_json.name}"),
        profile_path=Path(f"/app/profile/{profile.name}"),
        logger=logger
    )
    if not temp_json.exists() or error_code != "OK":        
        logger.error(f"JSON non généré pour : {temp_audio}")
        return None, error_code, error_message
    
    run_replaygain_in_container(audio_path=temp_audio, json_out_path=temp_json, profile_path=profile, logger=logger)
    result = parse_essentia_json(temp_json)
    return result, error_code, error_message