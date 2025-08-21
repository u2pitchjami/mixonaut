from __future__ import annotations

from utils.logger import with_child_logger
from pathlib import Path
from typing import Iterable, Optional

# Imports métier existants
from db.analyse.essentia_queries import (
    get_file_sha1_by_track,
    list_candidate_tracks_same_sha1,
    get_audio_hash_sha256_by_track,
    list_candidate_tracks_same_sha256,
)
from essentia.reuse.essentia_sav import (
    find_latest_sav_json,
    duplicate_essentia_json,
    load_essentia_json,
)

@with_child_logger
def _pick_latest_json(candidates: Iterable[int], logger=None) -> tuple[Optional[int], Optional[Path]]:
    """Retourne (donor_id, donor_json_path) avec le JSON le plus récent parmi les `candidates`.

    Args:
        candidates: itérable d'IDs track potentiels (donneurs)
        logger: logger applicatif
    """
    donor_json_path: Optional[Path] = None
    donor_id: Optional[int] = None
    for cand in candidates:
        cand_json = find_latest_sav_json(cand, logger=logger)
        if not cand_json:
            continue
        if donor_json_path is None or cand_json.stat().st_mtime > donor_json_path.stat().st_mtime:
            donor_json_path = cand_json
            donor_id = cand
    return donor_id, donor_json_path

@with_child_logger
def _apply_donor_to_dest(*, donor_id: int, donor_json: Path, dest_track_id: int, logger=None) -> Optional[Path]:
    """Copie le JSON Essentia du donneur vers la destination (sans post-analyse).

    Returns:
        Path du fichier JSON copié, ou None si échec.
    """
    copied = duplicate_essentia_json(
        donor_track_id=donor_id,
        dest_track_id=dest_track_id,
        logger=logger,
        patch_track_id=True
    )
    if not copied:
        return None

    donor_data = load_essentia_json(donor_json, logger=logger)
    if donor_data is None:
        return None

    # Renvoie le chemin du JSON copié
    return donor_json

    # # Rejoue la post-analyse sans relancer Essentia           
    # track_features, error_code, error_message = analyse_track_wo_essentia(
    #     json_path=donor_json, track_id=dest_track_id, force=True, logger=logger
    # )
    # if track_features is None:
    #         update_table_status("audio_features", track_id, error_code or "KO_FILE", error_message, logger=logger)
    #         logger.warning("❌ Analyse échouée pour le morceau : %s", track_id)
    
    # sync_fields_by_track_id(track_id=dest_track_id, track_features=track_features, logger=logger)    
    # transpo_data, err_code, err_msg = generate_transpositions(track_id=dest_track_id, logger=logger)
    # if transpo_data is None:
    #     # KO_UNSUPPORTED si pas de key/bpm exploitable
    #     # KO_FILE si erreur technique
    #     update_table_status("track_transpositions", dest_track_id, err_code or "KO_UNSUPPORTED", err_msg, logger=logger)
    # else:
    #     update_table_status("track_transpositions", dest_track_id, "OK", None, logger=logger)
    # return True

@with_child_logger
def try_reuse_essentia(track_id: int, *, logger=None) -> Optional[Path]:
    """Tente de réutiliser des features Essentia existantes pour `track_id`.

    Returns:
        Path du JSON copié si réutilisation réussie, sinon None.
    """
    # SHA1 strategy
    sha1 = get_file_sha1_by_track(track_id=track_id, logger=logger)
    if sha1:
        candidates = list_candidate_tracks_same_sha1(sha1, exclude_track_id=track_id, logger=logger)
        donor_id, donor_json = _pick_latest_json(candidates, logger=logger)
        if donor_id and donor_json:
            json_path = _apply_donor_to_dest(donor_id=donor_id, donor_json=donor_json, dest_track_id=track_id, logger=logger)
            if json_path:
                logger.info("♻️ Reuse via file_sha1=%s — donor=%s → dest=%s", sha1, donor_id, track_id)
                return json_path

    # SHA256 strategy
    audio_hash = get_audio_hash_sha256_by_track(track_id=track_id, logger=logger)
    if audio_hash:
        candidates = list_candidate_tracks_same_sha256(audio_hash, exclude_track_id=track_id, logger=logger)
        donor_id, donor_json = _pick_latest_json(candidates, logger=logger)
        if donor_id and donor_json:
            json_path = _apply_donor_to_dest(donor_id=donor_id, donor_json=donor_json, dest_track_id=track_id, logger=logger)
            if json_path:
                logger.info("♻️ Reuse via audio_hash=%s — donor=%s → dest=%s", audio_hash, donor_id, track_id)
                return json_path

    return None