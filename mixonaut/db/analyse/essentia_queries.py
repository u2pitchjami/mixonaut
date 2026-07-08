"""
2025-08-19 queries pour le process essentia.

module utilisé par :
    - analyse_batch.py
"""

from __future__ import annotations

import sqlite3
from typing import Any, TypeAlias

from mixonaut.db.access import execute_query, select_all, select_one
from mixonaut.utils.config import EDM_GENRES, EFFECTIVE_STATUS_LIST
from mixonaut.utils.logger import LoggerProtocol, ensure_logger

SqlParam: TypeAlias = int | float | str | bytes | None


def get_all_track_ids(logger: LoggerProtocol | None = None) -> list[int]:
    """
    Requête de récup de toutes les id de audio_features.
    """
    logger = ensure_logger(logger, __name__)
    rows = select_all("SELECT id FROM audio_features", (), logger=logger)

    return [row[0] for row in rows] or []


def fetch_tracks(
    missing_features: bool = False,
    mf_logic: str = "OR",
    status_list: list[str] | None = None,
    is_edm: bool = False,
    missing_field: str | None = None,
    path_contains: str | None = None,
    track_id: int | None = None,
    exclude_claimed: bool = True,
    logger: LoggerProtocol | None = None,
) -> list[sqlite3.Row]:
    """
    Récupère les pistes selon divers critères.

    Retourne une liste de sqlite3.Row : id, path, artist, title, album, essentia_status, madmom_status,
    transposition_status, hash_status, duration.

    Si exclude_claimed=True, exclut les tracks déjà réservées dans track_claims avec un expires_at encore actif.
    """
    logger = ensure_logger(logger, __name__)

    base_query = """
    SELECT
        v.id,
        v.path,
        v.artist,
        v.title,
        v.album,
        v.essentia_status,
        v.madmom_status,
        v.transposition_status,
        v.hash_status,
        v.duration
    FROM v_analyse AS v
    LEFT JOIN track_claims AS tc
        ON tc.track_id = v.id
       AND tc.expires_at > datetime('now')
    """

    where_clauses: list[str] = []
    params: list[SqlParam] = []

    # 0) Exclusion des tracks déjà claimées
    # Sauf éventuellement si on cible explicitement une track_id.
    if exclude_claimed and track_id is None:
        where_clauses.append("tc.track_id IS NULL")

    # 1) Filtre direct par track_id
    if track_id is not None:
        where_clauses.append("v.id = ?")
        params.append(track_id)

    # 2) Statuts Essentia / analyses
    effective_status_list: list[str] | None = None
    if status_list and len(status_list) > 0:
        effective_status_list = status_list
    elif missing_features:
        effective_status_list = EFFECTIVE_STATUS_LIST

    if effective_status_list:
        clause, p = build_status_filter(effective_status_list, logic=mf_logic)
        if clause:
            where_clauses.append(clause)
            params.extend(p)

    # 3) Champ manquant
    if missing_field:
        allowed_fields = {
            "bpm",
            "energy_level",
            "mood",
            "beat_intensity",
            "initial_key",
            "rg_track_gain",
            "genre",
        }
        if missing_field not in allowed_fields:
            raise ValueError(f"Champ interdit : {missing_field}")

        where_clauses.append(f"(v.{missing_field} IS NULL OR v.{missing_field} = '')")

    # 4) Filtre sur le chemin
    if path_contains:
        where_clauses.append("CAST(v.path AS TEXT) LIKE ? COLLATE NOCASE")
        params.append(f"%{path_contains}%")

    # 5) Genres EDM
    if is_edm:
        edm_clauses = ["v.genre LIKE ?" for _ in EDM_GENRES]
        where_clauses.append(f"({' OR '.join(edm_clauses)})")
        params.extend([f"%{genre}%" for genre in EDM_GENRES])

    # Finalisation de la requête
    if where_clauses:
        base_query += " WHERE " + " AND ".join(where_clauses)

    try:
        rows = execute_query(base_query, tuple(params), fetch=True, logger=logger)
        assert rows is not None
        return rows
    except Exception as e:  # pylint: disable=broad-except
        if logger:
            logger.error("Erreur dans fetch_tracks : %s", e)
        raise


def build_status_filter(
    effective_status_list: list[str] | None, logic: str = "OR"
) -> tuple[str | None, list[str]]:
    """
    Construction du filtre de status des analyses.
    """
    if not effective_status_list:
        return None, []

    placeholders = ",".join(["?"] * len(effective_status_list))
    clause = (
        f"(essentia_status IN ({placeholders}) "
        f"{logic} madmom_status IN ({placeholders}) "
        f"{logic} transposition_status IN ({placeholders}) "
        f"{logic} hash_status IN ({placeholders}))"
    )
    params = effective_status_list * 4
    return clause, params


def insert_or_update_audio_features(
    item_id: int,
    features: dict[str, Any],
    force: bool = True,
    logger: LoggerProtocol | None = None,
) -> bool:
    """
    Requête d'insertion dans audio_features.
    """
    logger = ensure_logger(logger, __name__)
    try:
        if not features:
            logger.warning("Aucune feature fournie pour audio_features.")
            return False

        features_cleaned = {k: v for k, v in features.items() if v is not None}

        if not features_cleaned:
            logger.warning("Aucun champ valide pour audio_features.")
            return False

        # Vérifie si la ligne existe déjà
        check_query = "SELECT id FROM audio_features WHERE id = ?"
        exists = execute_query(check_query, (item_id,), fetch=True, logger=logger)

        field_list = ", ".join(features_cleaned.keys())
        placeholders = ", ".join("?" for _ in features_cleaned)
        values = list(features_cleaned.values())

        if exists:
            if force:
                assignments = ", ".join(f"{k} = ?" for k in features_cleaned)
            else:
                assignments = ", ".join(
                    f"{k} = CASE WHEN {k} IS NULL THEN ? ELSE {k} END"
                    for k in features_cleaned
                )

            update_query = f"""
                UPDATE audio_features
                SET {assignments}
                WHERE id = ?
            """
            # logger.debug(f"[UPDATE] {update_query} {values + [item_id]}")
            execute_query(update_query, tuple(values + [item_id]), logger=logger)
        else:
            insert_query = f"""
                INSERT INTO audio_features (id, {field_list})
                VALUES (?, {placeholders})
            """
            # logger.debug(f"[INSERT] {insert_query} {[item_id] + values}")
            execute_query(insert_query, tuple([item_id] + values), logger=logger)

        return True

    except Exception as e:
        logger.error(
            f"Erreur dans insert_or_update_audio_features pour ID {item_id} : {e}"
        )
        raise


def get_audio_duration_by_id(
    track_id: int, logger: LoggerProtocol | None = None
) -> sqlite3.Row | None:
    essentia_duration = select_one(
        "SELECT duration FROM audio_features WHERE id = ?",
        params=(track_id,),
        logger=logger,
    )
    return essentia_duration


def get_audio_features_by_id(
    track_id: int, logger: LoggerProtocol | None = None
) -> dict[str, Any] | None:
    """
    Requête de recup des features.
    """
    logger = ensure_logger(logger, __name__)
    query = "SELECT * FROM audio_features WHERE id = ?"
    rows = execute_query(query, (track_id,), fetch=True, logger=logger)

    if not rows:
        return None

    row = rows[0]  # On suppose un seul résultat

    # Obtenir les noms de colonnes (si execute_query ne le fait pas)
    columns_query = "PRAGMA table_info(audio_features)"
    columns_info = execute_query(columns_query, (), fetch=True, logger=logger)
    if not columns_info:
        return None
    column_names = [col[1] for col in columns_info]  # col[1] = name

    return dict(zip(column_names, row))


def get_all_audio_features(
    logger: LoggerProtocol | None = None,
) -> list[sqlite3.Row]:
    """
    Récupère toutes les features audio.
    """
    logger = ensure_logger(logger, __name__)

    query = """
    SELECT *
    FROM audio_features
    """

    return select_all(
        query,
        logger=logger,
    )


# def nb_query(table: str = "audio_features") -> dict:
#     query = f"SELECT * FROM {table}"
#     rows = execute_query(query, (), fetch=True)

#     if not rows:
#         return None

#     nb = len(rows)

#     return nb


def count_existing_features(
    track_ids: list[int], logger: LoggerProtocol | None = None
) -> int:
    """
    Retourne le nombre de tracks présents dans audio_features pour les ids fournis.
    """
    logger = ensure_logger(logger, __name__)
    if not track_ids:
        return 0

    placeholders = ",".join(["?"] * len(track_ids))
    query = f"SELECT COUNT(*) FROM audio_features WHERE id IN ({placeholders})"

    try:
        result = select_one(query, params=tuple(track_ids), logger=logger)
        return result[0] if result else 0
    except Exception as e:
        logger.error(f"Erreur dans count_existing_features : {e}")
        return 0


# db/essentia_queries.py (AJOUTS)

SQL_GET_SHA1_BY_TRACK = """
SELECT file_sha1 FROM audio_hash WHERE id = ?;
"""

SQL_FIND_TRACKS_WITH_SAME_SHA1_EXCEPT = """
SELECT id
FROM audio_hash
WHERE file_sha1 = ? AND id != ?;
"""


def get_file_sha1_by_track(
    track_id: int, logger: LoggerProtocol | None = None
) -> str | None:
    """
    Requête de match sha1.
    """
    logger = ensure_logger(logger, __name__)
    row = select_one(SQL_GET_SHA1_BY_TRACK, (track_id,), logger=logger)
    return row[0] if row else None


def list_candidate_tracks_same_sha1(
    file_sha1: str, exclude_track_id: int, logger: LoggerProtocol | None = None
) -> list[int]:
    """
    Requête de match sha1.
    """
    logger = ensure_logger(logger, __name__)
    rows = select_all(
        SQL_FIND_TRACKS_WITH_SAME_SHA1_EXCEPT,
        (file_sha1, exclude_track_id),
        logger=logger,
    )
    return [r[0] for r in rows] if rows else []


SQL_GET_SHA256_BY_TRACK = """
SELECT audio_hash_sha256 FROM audio_hash WHERE id = ?;
"""

SQL_FIND_TRACKS_WITH_SAME_SHA256_EXCEPT = """
SELECT id
FROM audio_hash
WHERE audio_hash_sha256 = ?;
"""


def get_audio_hash_sha256_by_track(
    track_id: int, logger: LoggerProtocol | None = None
) -> str | None:
    """
    Requête de match sha256.
    """
    logger = ensure_logger(logger, __name__)
    row = select_one(SQL_GET_SHA256_BY_TRACK, (track_id,), logger=logger)
    return row[0] if row else None


def list_candidate_tracks_same_sha256(
    audio_hash_sha256: str, exclude_track_id: int, logger: LoggerProtocol | None = None
) -> list[int]:
    """
    Requête de match sha256.
    """
    logger = ensure_logger(logger, __name__)
    rows = select_all(
        SQL_FIND_TRACKS_WITH_SAME_SHA256_EXCEPT, (audio_hash_sha256,), logger=logger
    )
    return [r[0] for r in rows] if rows else []
