"""
2025-08-20.

hub analyse essentia.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from sqlite3 import Row
from mixonaut.db.analyse.madmom_queries import insert_or_update_audio_features
from mixonaut.madmom.analyse.madmom_extractions import (
    parse_madmom_json,
    run_madmom_extraction,
)
from mixonaut.madmom.features.madmom_enrich import (
    enrich_features_madmom,
    get_best_duration,
)
from mixonaut.madmom.analyse.prep_madmom_analyse import (
    archive_json_result,
)
from mixonaut.utils.logger import LoggerProtocol, ensure_logger
from mixonaut.utils.config import MADMOM_TEMP_JSON, MADMOM_MOUNT_CONTAINER


def extract_duration(value: Any) -> float | None:
    if value is None:
        return None

    if isinstance(value, Row):
        raw_duration = value["duration"]
    elif isinstance(value, tuple):
        raw_duration = value[0]
    else:
        raw_duration = value

    if raw_duration is None:
        return None

    try:
        duration = float(raw_duration)
    except (TypeError, ValueError):
        return None

    return duration if duration > 0 else None


def analyse_track_wo_madmom(
    json_path: str | Path,
    track_id: int,
    file_path: Path,
    duration: float | None,
    force: bool = False,
    logger: LoggerProtocol | None = None,
) -> tuple[dict[str, Any] | None, str | None, str | None]:
    """
    Charge un JSON Madmom déjà produit, calcule les features dérivées et met à jour la base. Ne lance PAS docker/Madmom.

    Returns:
        dict des features si OK, sinon None.
    """
    logger = ensure_logger(logger, __name__)
    try:
        path = Path(json_path)
        if not path.exists():
            logger.warning(f"❌ JSON introuvable pour track {track_id}: {path}")
            return None, "KO_FILE", f"JSON introuvable : {path}"

        track_features = parse_madmom_json(path, logger=logger)

        if not track_features:
            logger.warning(f"❌ Aucune caractéristique extraite (track {track_id})")
            return None, "KO_AUDIO", "JSON vide ou invalide"

        # Enrichissements (BPM arrondi, key/scale normalisés, etc.)
        duration = get_best_duration(
            essentia_duration=duration,
            audio_path=file_path,
        )

        track_features = enrich_features_madmom(
            track_features, duration=duration, logger=logger
        )
        track_features["raw_json_path"] = str(path)
        insert_or_update_audio_features(
            track_id, track_features, force=force, logger=logger
        )
        return track_features, None, None

    except Exception as exc:  # pylint: disable=broad-except
        logger.exception(f"❌ Erreur traitement track {track_id}: {exc}")
        return None, "KO_FILE", str(exc)


def analyse_track_madmom(
    track_id: int,
    temp_audio: Path,
    temp_json: Path,
    duration: float | None,
    force: bool = False,
    logger: LoggerProtocol | None = None,
) -> tuple[dict[str, Any] | None, str | None, str | None]:
    """
    Analyse un morceau de musique pour extraire des caractéristiques Madmom.
    Args:
        track_id (int): L'ID du track à analyser.
        temp_audio (Path): Le chemin vers le fichier audio temporaire.
        temp_json (Path): Le chemin vers le fichier JSON temporaire.
        duration (float | None): La durée du morceau.
        force (bool): Vérifie si le traitement doit être répété même si les fichiers temporaires sont présents.
        logger: Objectif pour loguer les messages.

    Returns:
        dict des features extraitees si OK, sinon None.
    """
    logger = ensure_logger(logger, __name__)
    try:
        track_features, error_code, error_message = extract_and_parse_features(
            temp_audio, temp_json, logger=logger
        )
        if not track_features:
            logger.warning(
                f"❌ Erreur traitement track {track_id} : Aucune caractéristique extraite"
            )
            return None, "KO_AUDIO", error_message or "JSON vide ou invalide"

        duration = get_best_duration(
            essentia_duration=duration,
            audio_path=temp_audio,
        )

        track_features = enrich_features_madmom(
            track_features, duration=duration, logger=logger
        )
        safe_name = temp_json.stem
        final_json_path = archive_json_result(track_id, safe_name, logger=logger)
        track_features["raw_json_path"] = str(final_json_path)
        insert_or_update_audio_features(
            track_id, track_features, force=force, logger=logger
        )

        return track_features, None, None

    except Exception as e:
        logger.exception(f"❌ Erreur traitement track {track_id} : {e}")
        return None, "KO_FILE", str(e)


def extract_and_parse_features(
    temp_audio: Path,
    temp_json: Path,
    logger: LoggerProtocol | None = None,
) -> tuple[dict[str, Any] | None, str, str | None]:
    """
    Lance l'image madmom et parse le json obtenu.
    """
    json_path = Path(f"{MADMOM_TEMP_JSON}/{temp_json.name}")
    logger = ensure_logger(logger, __name__)
    error_code, error_message = run_madmom_extraction(
        audio_path=Path(f"{MADMOM_MOUNT_CONTAINER}/{temp_audio.name}"),
        json_path=json_path,
        logger=logger,
    )
    if not json_path.exists() or error_code != "OK":
        logger.error(f"JSON non généré pour : {temp_audio}")
        return None, error_code, error_message

    result = parse_madmom_json(json_path)
    return result, error_code, error_message
