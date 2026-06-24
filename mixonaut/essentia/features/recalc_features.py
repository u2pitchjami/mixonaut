"""
2025-08-20.

modules de recalcul des features.
"""

from collections.abc import Callable, Mapping
from typing import Any

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
from mixonaut.utils.logger import LoggerProtocol, ensure_logger
from mixonaut.utils.utils_div import convert_path_format, sanitize_value, ensure_to_path

Features = dict[str, Any]
CalcFunc = Callable[[Features], Any]


def calc_initial_key(f: dict[str, Any]) -> str | None:
    best = get_best_key_from_essentia(f)
    if not best or best["key"] is None or best["scale"] is None:
        return None
    value = sanitize_value(convert_to_camelot(best["key"], best["scale"]), "key")
    return value if isinstance(value, str) or value is None else None


AVAILABLE_CALCS: Mapping[str, CalcFunc] = {
    "beat_intensity": calculate_beat_intensity,  # -> float
    "mood": lambda f: get_dominant_mood(compute_mood_vector(f)),  # -> str | None
    "genre": get_dominant_genre,  # -> str | None
    "initial_key": calc_initial_key,  # -> str | None
}


def sync_fields_by_track_id(
    track_id: int,
    track_features: dict[str, Any],
    items_columns: set[str],
    no_tags: bool | None = None,
    logger: LoggerProtocol | None = None,
) -> None:
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
        normalized_path = ensure_to_path(path)

        new_path = convert_path_format(
            path=normalized_path,
            to_beets=False,
        )
        # new_path = convert_path_format(path=str(path), to_beets=False)
        logger.debug("🏷️ Ecriture des tags")
        write_tags_docker(path=str(new_path), track_features=sync_fields, logger=logger)

    logger.debug("🏁 Retro_Beets_Db : TERMINE \n")


def main_recalc(
    track_id: int,
    recalc_fields: list[str],
    items_columns: set[str],
    no_tags: bool | None = None,
    logger: LoggerProtocol | None = None,
) -> None:
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
                calc_fn = AVAILABLE_CALCS.get(field)  # type: CalcFunc | None
                if calc_fn is None:
                    logger.warning("⚠️ Champ non reconnu : %s", field)
                    continue

                value = calc_fn(features)  # type: Any
                features[field] = value
                logger.debug("✅ %s recalculé : %s", field, features[field])
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
