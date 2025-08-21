"""
2020-08-20 module de traitemments de la synchro beets.
"""

# import re

from pathlib import Path

from mixonaut.beets_utils.commands.update_beets_fields import update_beets_fields
from mixonaut.db.beets.db_beets_queries import get_item_field_value
from mixonaut.process_analyse.retro_beets.write_tags import write_tags_docker
from mixonaut.utils.config import RETRO_MIXONAUT_BEETS
from mixonaut.utils.logger import LoggerProtocol, ensure_logger, with_child_logger
from mixonaut.utils.utils_div import convert_path_format, ensure_to_str


@with_child_logger
def sync_fields_by_track_id(
    track_id: int, track_features: dict, logger: LoggerProtocol | None = None
):
    """
    Sync fields for a given track ID.

    Parameters:
    - track_id (int): The ID of the track to sync.
    - track_features (dict): A dictionary containing features about the track.
    - logger (LoggerProtocol | None): A logging object, optional. Defaults to None.

    Returns:
    None
    """
    logger = ensure_logger(logger, __name__)
    path = get_item_field_value("path", track_id, logger=logger)
    if not path:
        logger.warning(f"⚠️ Impossible de retrouver le chemin du morceau {track_id}")
        return

    path_str = ensure_to_str(path)
    sync_fields = build_sync_fields(
        track_id=track_id, track_features=track_features, logger=logger
    )
    sync_beets_from_essentia(
        track_path=path_str, field_values=sync_fields, logger=logger
    )


@with_child_logger
def sync_beets_from_essentia(
    track_path: str, field_values, no_tags=None, logger: LoggerProtocol | None = None
):
    """
    Synchronise Beets fields from Essentia.
    Args:
        track_path (str): Path of the track.
        field_values: Values to be written in the Beets database.
        no_tags (bool, optional): Whether to not write tags. Defaults to None.

    Raises:
        Exception: If an error occurs during the update process.
    """
    logger = ensure_logger(logger, __name__)
    logger.debug(f"💾 Mise à jour de la base Beets field_values {field_values}")
    try:
        update_beets_fields(
            track_path=track_path, logger=logger, field_values=field_values
        )
    except Exception as e:
        logger.error(f"❌ Erreur lors de la mise à jour des champs Beets : {e}")
        raise
    if not no_tags:
        new_path = convert_path_format(path=Path(track_path), to_beets=False)
        logger.debug("🏷️ Ecriture des tags")
        write_tags_docker(
            path=str(new_path), track_features=field_values, logger=logger
        )

    logger.debug("🏁 Retro_Beets_Db : TERMINE \n")


@with_child_logger
def build_sync_fields(
    track_id: int,
    track_features: dict,
    extra_fields=None,
    logger: LoggerProtocol | None = None,
) -> dict:
    """
    Builds the sync fields for a given track ID.

    This function iterates over all fields in RETRO_MIXONAUT_BEETS and
    their corresponding values in track_features. It then checks each field
    to see if it should be updated using the function `should_update_<field>`.
    If the update check returns False, the field is skipped. If it returns a new
    value, that value is used instead.

    Args:
        track_id (int): The ID of the track.
        track_features (dict): A dictionary containing the features of the track.
        extra_fields (set, optional): Additional fields to check for updates.
            Defaults to None.
        logger: A LoggerProtocol instance. Defaults to None.

    Returns:
        dict: A dictionary containing the sync fields for the given track ID.
    """
    logger = ensure_logger(logger, __name__)
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


# @with_child_logger
# def should_update_genre(track_id: int, new_genre: str, logger: str = None) -> bool:
#     logger.debug(f"should_update_genre new_genre : {new_genre}")
#     current_genre = get_item_field_value("genre", track_id, logger=logger)
#     logger.debug(f"current_genre : {current_genre}")
#     if not current_genre:
#         return new_genre.strip()

#     # Nettoyage des genres actuels
#     current_genres = [g.strip() for g in re.split(r"[;,/]", current_genre)]
#     new_genre_clean = new_genre.strip()
#     logger.debug(f"current_genre : {current_genre}")
#     logger.debug(f"new_genre_clean : {new_genre_clean}")

#     if new_genre_clean in current_genres:
#         return False  # Rien à faire

#     # Sinon, on ajoute à la liste
#     genres = current_genres + [new_genre_clean]
#     logger.debug(f"Genres après ajout : {genres}")
#     # Mise en forme (capitalisation facultative)
#     new_value = ", ".join(sorted(set(genres)))  # tri optionnel
#     logger.debug(f"new_value : {new_value}")
#     return new_value

# @with_child_logger
# def should_update_bpm(track_id: int, bpm: str, logger: str = None) -> bool:
#     try:
#         bpm_float = float(bpm)
#         bpm_int = int(round(bpm_float))
#         return bpm_int
#     except (ValueError, TypeError) as e:
#         if logger:
#             logger.warning(f"❌ Impossible de convertir bpm '{value}' en entier : {e}")
#         return None
