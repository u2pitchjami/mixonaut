import argparse
from db.essentia_queries import get_audio_features_by_id, insert_or_update_audio_features
from db.db_beets_queries import get_item_field_value
from essentia.essentia_calculate import calculate_beat_intensity, compute_energy_level
from essentia.essentia_mood import compute_mood_vector
from essentia.essentia_key import get_best_key_from_essentia, convert_to_camelot
from essentia.essentia_genre import get_dominant_genre
from beets_utils.update_beets_fields import update_beets_field
from utils.utils_div import ensure_to_str
from logic.sync_beets_from_essentia import sync_beets_from_essentia, build_sync_fields
from utils.logger import get_logger

logname = "Essentia_Recalc"
logger = get_logger(logname)

AVAILABLE_CALCS = {
    "beat_intensity": calculate_beat_intensity,
    "energy_level": compute_energy_level,
    "mood": lambda f: get_dominant_mood(compute_mood_vector(f)),
    "genre": get_dominant_genre,
    "initial_key": lambda f: convert_to_camelot(**get_best_key_from_essentia(f))
}

def sync_fields_by_track_id(track_id: int, track_features: dict, no_tags = None):
    path = get_item_field_value("path", track_id)
    if not path:
        logger.warning(f"⚠️ Chemin introuvable pour track {track_id}")
        return
    path_str = ensure_to_str(path)
    sync_fields = build_sync_fields(track_id, track_features)
    sync_beets_from_essentia(path_str, sync_fields, no_tags=no_tags, logname="Essentia_Recalc")

def main_recalc(track_id: int, recalc_fields: list, no_tags = None):
    features = get_audio_features_by_id(track_id)
    
    logger.debug(f"🔍 Recalcul des champs pour track {track_id} : {recalc_fields}")
    if not features:
        logger.warning(f"❌ Aucune donnée Essentia pour track {track_id}")
        return

    for field in recalc_fields:
        logger.debug(f"🔄 Recalcul du champ : {field}")
        calc_fn = AVAILABLE_CALCS.get(field)
        logger.debug(f"🔄 calc_fn : {calc_fn}")
        if not calc_fn:
            logger.warning(f"⚠️ Champ non reconnu : {field}")
            continue
        try:
            features[field] = calc_fn(features)
            logger.debug(f"✅ {field} recalculé : {features[field]}")
        except Exception as e:
            logger.warning(f"❌ Erreur recalcul {field} : {e}")
    insert_or_update_audio_features(track_id, features, logname=logname)
    sync_fields_by_track_id(track_id, features, no_tags=no_tags)
