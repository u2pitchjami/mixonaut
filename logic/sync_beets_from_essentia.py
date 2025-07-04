
from logic.write_tags import write_tags_docker
from beets_utils.update_beets_fields import update_beets_fields
from db.db_beets_queries import get_item_field_value
from utils.utils_div import convert_path_format, ensure_to_str
from utils.config import RETRO_MIXONAUT_BEETS
from pathlib import Path
import re
from utils.logger import get_logger, with_child_logger

@with_child_logger
def sync_fields_by_track_id(track_id: int, track_features: dict, logger: str = None):
    path = get_item_field_value("path", track_id, logger=logger)
    if not path:
        logger.warning(f"⚠️ Impossible de retrouver le chemin du morceau {track_id}")
        return

    path_str = ensure_to_str(path)
    sync_fields = build_sync_fields(track_id=track_id, track_features=track_features, logger=logger)
    sync_beets_from_essentia(track_path=path_str, field_values=sync_fields, logger=logger)

@with_child_logger
def sync_beets_from_essentia(track_path: str, field_values, no_tags=None,  logger=None):
    logger.debug(f"💾 Mise à jour de la base Beets field_values {field_values}")
    try:
        update_beets_fields(
            track_path=track_path,
            logger=logger,
            field_values=field_values
        )
    except Exception as e:
        logger.error(f"❌ Erreur lors de la mise à jour des champs Beets : {e}")
        raise
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
def build_sync_fields(track_id: int, track_features: dict, extra_fields=None, logger=None) -> dict:
    fields_to_check = set(RETRO_MIXONAUT_BEETS)
    logger.debug(f"Initial fields to check: {fields_to_check}")
    if extra_fields:
        fields_to_check.update(extra_fields)

    result = {}

    for field in fields_to_check:
        logger.debug(f"Processing field: {field}")
        value = track_features.get(field)
        logger.debug(f"Processing field: {field}, value: {value}")
        if value is None:
            continue

        # On cherche une fonction should_update_<field>
        func_name = f"should_update_{field}"
        check_fn = globals().get(func_name)

        if check_fn:
            check_result = check_fn(track_id, value, logger=logger)
            if check_result is False:
                continue
            elif check_result is not True:
                value = check_result  # la fonction a renvoyé une nouvelle valeur

        result[field] = value
        
    return result

@with_child_logger
def should_update_genre(track_id: int, new_genre: str, logger: str = None) -> bool:
    logger.debug(f"should_update_genre new_genre : {new_genre}")
    current_genre = get_item_field_value("genre", track_id, logger=logger)
    logger.debug(f"current_genre : {current_genre}")
    if not current_genre:
        return new_genre.strip()
    
    # Nettoyage des genres actuels
    current_genres = [g.strip() for g in re.split(r"[;,/]", current_genre)]
    new_genre_clean = new_genre.strip()
    logger.debug(f"current_genre : {current_genre}")
    logger.debug(f"new_genre_clean : {new_genre_clean}")

    if new_genre_clean in current_genres:
        return False  # Rien à faire

    # Sinon, on ajoute à la liste
    genres = current_genres + [new_genre_clean]
    logger.debug(f"Genres après ajout : {genres}")
    # Mise en forme (capitalisation facultative)
    new_value = ", ".join(sorted(set(genres)))  # tri optionnel
    logger.debug(f"new_value : {new_value}")    
    return new_value

@with_child_logger
def should_update_bpm(track_id: int, bpm: str, logger: str = None) -> bool:
    try:
        bpm_float = float(bpm)
        bpm_int = int(round(bpm_float))
        return bpm_int
    except (ValueError, TypeError) as e:
        if logger:
            logger.warning(f"❌ Impossible de convertir bpm '{value}' en entier : {e}")
        return None