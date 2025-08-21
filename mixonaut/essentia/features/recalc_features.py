"""
2025-08-20.

modules de recalcul des features.
"""

from pathlib import Path

from mixonaut.db.analyse.essentia_queries import (
    get_audio_features_by_id,
    insert_or_update_audio_features,
)
from mixonaut.db.beets.db_beets_queries import (
    get_item_field_value,
    retro_inject_features,
)
from mixonaut.essentia.features.essentia_calculate import calculate_beat_intensity
from mixonaut.essentia.features.essentia_genre import get_dominant_genre
from mixonaut.essentia.features.essentia_key import (
    convert_to_camelot,
    get_best_key_from_essentia,
)
from mixonaut.essentia.features.essentia_mood import (
    compute_mood_vector,
    get_dominant_mood,
)
from mixonaut.process_analyse.retro_beets.sync_beets_from_essentia import (
    build_sync_fields,
)
from mixonaut.process_analyse.retro_beets.write_tags import write_tags_docker
from mixonaut.process_analyse.transposition.transposition import generate_transpositions
from mixonaut.utils.logger import LoggerProtocol, ensure_logger, with_child_logger
from mixonaut.utils.utils_div import convert_path_format, sanitize_value

# Essentia recalc
AVAILABLE_CALCS = {
    "beat_intensity": calculate_beat_intensity,
    "mood": lambda f: get_dominant_mood(compute_mood_vector(f)),
    "genre": get_dominant_genre,
    "initial_key": lambda f: sanitize_value(
        convert_to_camelot(**get_best_key_from_essentia(f)), "key"
    ),
}


@with_child_logger
def sync_fields_by_track_id(
    track_id: int,
    track_features: dict,
    items_columns: set,
    no_tags=None,
    logger: LoggerProtocol | None = None,
):
    """
    Synchronise les features d'un track avec Beets.

    Parameters
    ----------
    track_id : int
        L'ID du track à synchroniser.
    track_features : dict
        Les features du track à synchroniser.
    items_columns : set
        Les colonnes des données à traiter.
    no_tags : bool, optional
        Si la synchronisation doit inclure ou exclure les tags. Par défaut, les tags sont inclus.

    Returns
    -------
    None

    Notes
    -----
    Cette fonction s'assure que les features du track sont à jour et les écrit sur Beets.
    """
    logger = ensure_logger(logger, __name__)
    path = get_item_field_value("path", track_id, logger=logger)
    if not path:
        logger.warning(f"⚠️ Chemin introuvable pour track {track_id}")
        return
    sync_fields = build_sync_fields(track_id, track_features, logger=logger)
    logger.debug(f"🔍 sync_fields {sync_fields}")
    retro_inject_features(
        track_id=track_id,
        features=sync_fields,
        items_columns=items_columns,
        logger=logger,
    )
    if not no_tags:
        new_path = convert_path_format(path=str(path), to_beets=False)
        logger.debug("🏷️ Ecriture des tags")
        write_tags_docker(path=str(new_path), track_features=sync_fields, logger=logger)

    logger.debug("🏁 Retro_Beets_Db : TERMINE \n")


@with_child_logger
def main_recalc(
    track_id: int,
    recalc_fields: list,
    items_columns: set,
    no_tags=None,
    logger: LoggerProtocol | None = None,
):
    """
    Recalculate the specified features for a given track ID.

    Parameters:
        track_id (int): The ID of the track to recalibrate.
        recalc_fields (list): A list of feature names to recalculate.
        items_columns (set): A set of columns related to the tracks.
        no_tags (bool, optional): If True, do not write tags. Defaults to None.
        logger (LoggerProtocol | None, optional): The logger instance. Defaults to None.
    Returns:
        None
    """
    logger = ensure_logger(logger, __name__)
    try:
        features = get_audio_features_by_id(track_id, logger=logger)
        logger.debug(f"🔍 Recalcul des champs pour track {track_id} : {recalc_fields}")

        if not features:
            logger.warning(f"❌ Aucune donnée Essentia pour track {track_id}")
            return

        for field in recalc_fields:
            logger.debug(f"🔄 Recalcul du champ : {field}")
            try:
                calc_fn = AVAILABLE_CALCS.get(field)
                if not calc_fn:
                    logger.warning(f"⚠️ Champ non reconnu : {field}")
                    continue

                features[field] = calc_fn(features)
                logger.debug(f"✅ {field} recalculé : {features[field]}")
            except Exception as e:
                logger.warning(f"❌ Erreur recalcul {field} : {e}")

        insert_or_update_audio_features(track_id, features, logger=logger)
        sync_fields_by_track_id(
            track_id=track_id,
            track_features=features,
            items_columns=items_columns,
            no_tags=no_tags,
            logger=logger,
        )

        if "initial_key" in recalc_fields:
            try:
                logger.info(
                    f"🔁 Recalcul des transpositions pour track {track_id} (clé modifiée)"
                )
                generate_transpositions(track_id=track_id, logger=logger)
            except Exception as e:
                logger.warning(
                    f"❌ Erreur lors du recalcul des transpositions pour track {track_id} : {e}"
                )

    except Exception:
        logger.exception(f"Erreur inattendue dans main_recalc pour track {track_id}")
        raise
