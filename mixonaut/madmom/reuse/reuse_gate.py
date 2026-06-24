"""
2025-08-20 module de recherche et récupération du json.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

# Imports métier existants
from mixonaut.db.analyse.essentia_queries import (
    get_audio_hash_sha256_by_track,
    get_file_sha1_by_track,
    list_candidate_tracks_same_sha1,
    list_candidate_tracks_same_sha256,
)
from mixonaut.madmom.reuse.madmom_sav import (
    find_latest_sav_json,
    duplicate_madmom_json,
    load_madmom_json,
)
from mixonaut.utils.logger import LoggerProtocol, ensure_logger


def _pick_latest_json(
    candidates: Iterable[int], logger: LoggerProtocol | None = None
) -> tuple[int | None, Path | None]:
    """
    Retourne (donor_id, donor_json_path) avec le JSON le plus récent parmi les `candidates`.

    Args:
        candidates: itérable d'IDs track potentiels (donneurs)
        logger: logger applicatif
    """
    logger = ensure_logger(logger, __name__)
    donor_json_path: Path | None = None
    donor_id: int | None = None
    for cand in candidates:
        cand_json = find_latest_sav_json(cand, logger=logger)
        if not cand_json:
            continue
        if (
            donor_json_path is None
            or cand_json.stat().st_mtime > donor_json_path.stat().st_mtime
        ):
            donor_json_path = cand_json
            donor_id = cand
    return donor_id, donor_json_path


def _apply_donor_to_dest(
    *,
    donor_id: int,
    donor_json: Path,
    dest_track_id: int,
    logger: LoggerProtocol | None = None,
) -> Path | None:
    """
    Copie le JSON Essentia du donneur vers la destination (sans post- analyse).

    Returns:
        Path du fichier JSON copié, ou None si échec.
    """
    logger = ensure_logger(logger, __name__)
    copied = duplicate_madmom_json(
        donor_track_id=donor_id,
        dest_track_id=dest_track_id,
        logger=logger,
        patch_track_id=True,
    )
    if not copied:
        return None

    donor_data = load_madmom_json(donor_json, logger=logger)
    if donor_data is None:
        return None

    # Renvoie le chemin du JSON copié
    return donor_json


def try_reuse_madmom(
    track_id: int, *, logger: LoggerProtocol | None = None
) -> Path | None:
    """
    Tente de réutiliser des features Madmom existantes pour `track_id`.

    Returns:
        Path du JSON copié si réutilisation réussie, sinon None.
    """
    logger = ensure_logger(logger, __name__)
    # SHA1 strategy
    sha1 = get_file_sha1_by_track(track_id=track_id, logger=logger)
    if sha1:
        candidates = list_candidate_tracks_same_sha1(
            sha1, exclude_track_id=track_id, logger=logger
        )
        donor_id, donor_json = _pick_latest_json(candidates, logger=logger)
        if donor_id and donor_json:
            json_path = _apply_donor_to_dest(
                donor_id=donor_id,
                donor_json=donor_json,
                dest_track_id=track_id,
                logger=logger,
            )
            if json_path:
                logger.info(
                    "♻️ Reuse via file_sha1=%s — donor=%s → dest=%s",
                    sha1,
                    donor_id,
                    track_id,
                )
                return json_path

    # SHA256 strategy
    audio_hash = get_audio_hash_sha256_by_track(track_id=track_id, logger=logger)
    if audio_hash:
        candidates = list_candidate_tracks_same_sha256(
            audio_hash, exclude_track_id=track_id, logger=logger
        )
        donor_id, donor_json = _pick_latest_json(candidates, logger=logger)
        if donor_id and donor_json:
            json_path = _apply_donor_to_dest(
                donor_id=donor_id,
                donor_json=donor_json,
                dest_track_id=track_id,
                logger=logger,
            )
            if json_path:
                logger.info(
                    "♻️ Reuse via audio_hash=%s — donor=%s → dest=%s",
                    audio_hash,
                    donor_id,
                    track_id,
                )
                return json_path

    return None
