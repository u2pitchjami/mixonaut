# utils/essentia_sav.py
"""
Helpers pour gérer les JSON Essentia (SAV) :

- sharding par blocs de 1000
- recherche du JSON le plus récent pour un track_id (pattern <id>_*.json)
- duplication d'un JSON donneur -> destinataire (avec patch éventuel du track_id)
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from mixonaut.utils.config import (  # dossier destination des JSON archivés
    ESSENTIA_SAV_JSON,
)
from mixonaut.utils.logger import LoggerProtocol, ensure_logger


def _shard_dir(track_id: int) -> Path:
    """
    Retourne le dossier shard pour un track_id (par tranches de 1000).
    """
    base = Path(ESSENTIA_SAV_JSON)
    return base / f"{(track_id // 1000) * 1000:04d}"


def find_latest_sav_json(
    track_id: int, logger: LoggerProtocol | None = None
) -> Path | None:
    """
    Trouve le JSON SAV le plus récent pour un track_id.

    Pattern attendu: '<track_id>_*.json' dans le shard correspondant.
    """
    logger = ensure_logger(logger, __name__)
    shard = _shard_dir(track_id)
    if not shard.exists():
        logger.debug("SAV shard inexistant pour track_id=%s: %s", track_id, shard)
        return None
    candidates: list[Path] = sorted(
        shard.glob(f"{track_id}_*.json"), key=lambda p: p.stat().st_mtime, reverse=True
    )
    if not candidates:
        logger.debug("Aucun JSON SAV pour track_id=%s dans %s", track_id, shard)
        return None
    return candidates[0]


def _dest_name_from_donor(donor_path: Path, dest_track_id: int) -> str:
    """
    Construit un nom '<dest_id>_<suffixe_donneur>.json' en réutilisant le suffixe après l'ID du donneur.

    Si le nom ne matche pas le pattern, fallback sur '<dest_id>_reused.json'.
    """
    name = donor_path.name  # ex: 22786_carbon_based_lifeforms_irdial_irdial.json
    parts = name.split("_", 1)
    suffix = parts[1] if len(parts) == 2 else "reused.json"
    if not suffix.endswith(".json"):
        suffix += ".json"
    return f"{dest_track_id}_{suffix}"


def duplicate_essentia_json(
    donor_track_id: int,
    dest_track_id: int,
    *,
    logger: LoggerProtocol | None = None,
    patch_track_id: bool = True,
) -> Path | None:
    """
    Duplique le JSON SAV du donneur vers le destinataire.

    - recherche le JSON donneur le plus récent
    - crée le dossier shard du destinataire si nécessaire
    - copie le fichier en le renommant '<dest_id>_<suffixe_donneur>.json'
    - optionnellement : patch le champ 'track_id' dans le JSON (s'il existe)
    Retourne le chemin du JSON copié, ou None si échec/absent.
    """
    logger = ensure_logger(logger, __name__)
    donor_json = find_latest_sav_json(donor_track_id, logger)
    if donor_json is None:
        logger.warning(
            "♻️ Reuse annulé: JSON donneur introuvable (track_id=%s)", donor_track_id
        )
        return None

    dest_dir = _shard_dir(dest_track_id)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_name = _dest_name_from_donor(donor_json, dest_track_id)
    dest_json = dest_dir / dest_name

    if donor_track_id != dest_track_id:
        try:
            shutil.copy(donor_json, dest_json)
            logger.info("♻️ JSON dupliqué: %s → %s", donor_json, dest_json)
        except Exception:  # pylint: disable=broad-except
            logger.exception("Erreur copie JSON SAV: %s -> %s", donor_json, dest_json)
            return None

    if patch_track_id:
        try:
            with open(dest_json, encoding="utf-8") as f_in:
                data = json.load(f_in)
            if isinstance(data, dict) and "track_id" in data:
                data["track_id"] = dest_track_id
                with open(dest_json, "w", encoding="utf-8") as f_out:
                    json.dump(data, f_out, ensure_ascii=False, indent=2)
                logger.debug("Patched track_id dans JSON: %s", dest_json)
        except Exception:  # pylint: disable=broad-except
            logger.exception(
                "Patch du track_id dans %s a échoué (on garde la copie telle quelle)",
                dest_json,
            )

    return dest_json


def load_essentia_json(
    json_path: Path, logger: LoggerProtocol | None = None
) -> dict | None:
    """
    Charge un JSON Essentia en dict.

    Retourne None en cas d'erreur.
    """
    logger = ensure_logger(logger, __name__)
    try:
        with open(json_path, encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError:
        logger.warning("JSON introuvable: %s", json_path)
        return None
    except Exception:  # pylint: disable=broad-except
        logger.exception("Lecture JSON Essentia échouée: %s", json_path)
        return None
