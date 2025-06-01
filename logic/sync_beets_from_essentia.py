
from logic.write_tags import write_tags_docker
from beets_utils.update_beets_fields import update_beets_fields
from db.db_beets_queries import get_item_field_value
from utils.utils_div import convert_path_format, ensure_to_str
from utils.config import RETRO_MIXONAUT_BEETS
from pathlib import Path
import re
from utils.logger import get_logger
logname = __name__.split(".")[-1].capitalize()

def sync_fields_by_track_id(track_id: int, track_features: dict, logname: str = logname):
    logger = get_logger(logname)
    path = get_item_field_value("path", track_id)
    if not path:
        logger.warning(f"⚠️ Impossible de retrouver le chemin du morceau {track_id}")
        return

    path_str = ensure_to_str(path)
    sync_fields = build_sync_fields(track_id=track_id, track_features=track_features, logname=logname)
    sync_beets_from_essentia(track_path=path_str, field_values=sync_fields, logname=logname)

def sync_beets_from_essentia(track_path: str, field_values,  logname=logname):
    logger = get_logger(logname)
    
    logger.info(f"💾 Mise à jour de la base Beets field_values {field_values}")
    try:
        update_beets_fields(
            track_path=track_path,
            logname=logname,
            field_values=field_values
        )
    except Exception as e:
        logger.error(f"❌ Erreur lors de la mise à jour des champs Beets : {e}")
        raise
    
    new_path = convert_path_format(path=track_path, to_beets=False)
    print(f"🔄 Nouveau chemin converti : {new_path}")
    logger.info("🏷️ Ecriture des tags")
    write_tags_docker(
        path=new_path,
        track_features=field_values,
        logname=logname
    )

    logger.info("🏁 Retro_Beets_Db : TERMINE \n")
    
def build_sync_fields(track_id: int, track_features: dict, extra_fields=None, logname=logname) -> dict:
    logger = get_logger(logname)
    logger.debug(f"build_sync_fields called with track_id: {track_id}, track_features: {track_features}")
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

        # S'il y a une fonction de validation, on l'utilise
        if check_fn:
            if not check_fn(track_id, value):
                continue  # Ne pas synchroniser ce champ
        # Sinon, on considère qu'on peut le synchroniser
        result[field] = value

    return result

def should_update_genre(track_id: int, new_genre: str) -> bool:
    current_genre = get_item_field_value("genre", track_id)
    if not current_genre:
        return True
    
    current_genres = [g.strip().lower() for g in re.split(r"[;,/]", current_genre)]
    return new_genre.strip().lower() not in current_genres