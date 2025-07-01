from db.essentia_queries import get_audio_features_by_id, insert_or_update_audio_features
from db.db_beets_queries import get_item_field_value, retro_inject_features
from essentia.essentia_calculate import calculate_beat_intensity, compute_energy_level
from essentia.essentia_mood import compute_mood_vector, get_dominant_mood
from essentia.essentia_key import get_best_key_from_essentia, convert_to_camelot
from essentia.essentia_genre import get_dominant_genre
from beets_utils.update_beets_fields import update_beets_field
from logic.transposition import generate_transpositions
from logic.write_tags import write_tags_docker
from utils.utils_div import ensure_to_str, sanitize_value, convert_path_format
from logic.sync_beets_from_essentia import sync_beets_from_essentia, build_sync_fields
from utils.logger import get_logger, with_child_logger

AVAILABLE_CALCS = {
    "beat_intensity": calculate_beat_intensity,
    "mood": lambda f: get_dominant_mood(compute_mood_vector(f)),
    "genre": get_dominant_genre,
    
    "initial_key": lambda f: sanitize_value(
    convert_to_camelot(**get_best_key_from_essentia(f)),
    "key")
}

@with_child_logger
def sync_fields_by_track_id(track_id: int, track_features: dict, items_columns: set, no_tags = None, logger: str = None):
    path = get_item_field_value("path", track_id, logger=logger)
    if not path:
        logger.warning(f"⚠️ Chemin introuvable pour track {track_id}")
        return
    path_str = ensure_to_str(path)
    sync_fields = build_sync_fields(track_id, track_features, logger=logger)
    logger.debug(f"🔍 sync_fields {sync_fields}")
    retro_inject_features(track_id=track_id, features=sync_fields, items_columns=items_columns, logger=logger)
    if not no_tags:
        new_path = convert_path_format(path=track_path, to_beets=False)
        logger.debug("🏷️ Ecriture des tags")
        write_tags_docker(
            path=new_path,
            track_features=field_values,
            logger=logger
        )

    logger.debug("🏁 Retro_Beets_Db : TERMINE \n")
    
@with_child_logger
def main_recalc(track_id: int, recalc_fields: list, items_columns: set, no_tags=None, logger=None):
    try:
        features = get_audio_features_by_id(track_id, logger=logger)
        logger.debug(f"🔍 Recalcul des champs pour track {track_id} : {recalc_fields}")

        if not features:
            logger.warning(f"❌ Aucune donnée Essentia pour track {track_id}")
            return

        for field in recalc_fields:
            logger.debug(f"🔄 Recalcul du champ : {field}")
            calc_fn = AVAILABLE_CALCS.get(field)
            if not calc_fn:
                logger.warning(f"⚠️ Champ non reconnu : {field}")
                continue
            try:
                features[field] = calc_fn(features)
                logger.debug(f"✅ {field} recalculé : {features[field]}")
            except Exception as e:
                logger.warning(f"❌ Erreur recalcul {field} : {e}")

        insert_or_update_audio_features(track_id, features, logger=logger)
        sync_fields_by_track_id(track_id=track_id, track_features=features, items_columns=items_columns, no_tags=no_tags, logger=logger)

        if "initial_key" in recalc_fields:
            try:
                logger.info(f"🔁 Recalcul des transpositions pour track {track_id} (clé modifiée)")
                generate_transpositions(track_id=track_id, logger=logger)
            except Exception as e:
                logger.warning(f"❌ Erreur lors du recalcul des transpositions pour track {track_id} : {e}")

    except Exception:
        logger.exception(f"Erreur inattendue dans main_recalc pour track {track_id}")
        raise

