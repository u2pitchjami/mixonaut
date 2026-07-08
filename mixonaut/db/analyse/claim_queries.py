from __future__ import annotations

from datetime import datetime, timedelta

from mixonaut.utils.logger import LoggerProtocol, ensure_logger
from collections.abc import Sequence

from mixonaut.db.session import MixonautDBSession
from mixonaut.utils.config import BEETS_DB
from mixonaut.db.access import execute_write, select_scalar


def sqlite_datetime_text(dt: datetime | None = None) -> str:
    if dt is None:
        dt = datetime.now()
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def claim_tracks(
    track_ids: Sequence[int],
    worker_id: str,
    batch_id: str,
    run_source: str = "manual",
    ttl_hours: int = 6,
    db: str = BEETS_DB,
    logger: LoggerProtocol | None = None,
) -> list[int]:
    """
    Réserve temporairement un lot de tracks dans track_claims.

    Retourne uniquement les track_ids réellement réservés.

    Une track déjà claimée par une autre instance est ignorée grâce à :
    - PRIMARY KEY(track_id)
    - INSERT OR IGNORE
    """
    logger = ensure_logger(logger, __name__)

    if not track_ids:
        logger.debug("claim_tracks: aucune track à réserver")
        return []

    now = datetime.now()
    now_txt = sqlite_datetime_text(now)
    expires_at_txt = sqlite_datetime_text(now + timedelta(hours=ttl_hours))

    claimed_ids: list[int] = []

    with MixonautDBSession(db_path=db, logger=logger) as dbs:
        # 1) Nettoyage dans la même transaction
        dbs.execute(
            """
            DELETE FROM track_claims
            WHERE expires_at <= datetime('now');
            """
        )

        # 2) Claims
        for track_id in track_ids:
            cur = dbs.execute(
                """
                INSERT OR IGNORE INTO track_claims (
                    track_id,
                    worker_id,
                    batch_id,
                    run_source,
                    claimed_at,
                    expires_at,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    track_id,
                    worker_id,
                    batch_id,
                    run_source,
                    now_txt,
                    expires_at_txt,
                    now_txt,
                    now_txt,
                ),
            )

            if cur.rowcount == 1:
                claimed_ids.append(track_id)

    logger.info(
        "Claims créés : %d/%d tracks réservées | batch_id=%s | worker_id=%s | run_source=%s",
        len(claimed_ids),
        len(track_ids),
        batch_id,
        worker_id,
        run_source,
    )

    return claimed_ids


def cleanup_expired_track_claims(
    db: str = BEETS_DB,
    logger: LoggerProtocol | None = None,
) -> None:
    """
    Supprime les claims expirés.

    À appeler au début d'un batch avant de réserver de nouvelles tracks.
    """
    logger = ensure_logger(logger, __name__)

    execute_write(
        """
        DELETE FROM track_claims
        WHERE expires_at <= datetime('now');
        """,
        db=db,
        logger=logger,
    )

    logger.debug("Claims expirés nettoyés")


def release_track_claim(
    track_id: int,
    batch_id: str,
    db: str = BEETS_DB,
    logger: LoggerProtocol | None = None,
) -> None:
    """
    Libère le claim d'une track terminée pour ce batch.

    Le batch_id est inclus pour éviter de supprimer par erreur un claim qui aurait été repris par un autre batch.
    """
    logger = ensure_logger(logger, __name__)

    execute_write(
        """
        DELETE FROM track_claims
        WHERE track_id = ?
          AND batch_id = ?;
        """,
        params=(track_id, batch_id),
        db=db,
        logger=logger,
    )


def release_batch_claims(
    batch_id: str,
    db: str = BEETS_DB,
    logger: LoggerProtocol | None = None,
) -> None:
    """
    Libère tous les claims associés à un batch.

    Utile en fin normale de batch ou en nettoyage manuel.
    """
    logger = ensure_logger(logger, __name__)

    execute_write(
        """
        DELETE FROM track_claims
        WHERE batch_id = ?;
        """,
        params=(batch_id,),
        db=db,
        logger=logger,
    )

    logger.info("Claims libérés pour batch_id=%s", batch_id)


def refresh_track_claim(
    track_id: int,
    batch_id: str,
    ttl_hours: int = 6,
    db: str = BEETS_DB,
    logger: LoggerProtocol | None = None,
) -> None:
    """
    Prolonge le claim d'une track en cours de traitement.

    Utile pour éviter qu'une track très longue expire pendant que le batch est encore vivant.
    """
    logger = ensure_logger(logger, __name__)

    expires_at_txt = (datetime.now() + timedelta(hours=ttl_hours)).isoformat(
        timespec="seconds"
    )
    updated_at_txt = datetime.now().isoformat(timespec="seconds")

    execute_write(
        """
        UPDATE track_claims
        SET expires_at = ?,
            updated_at = ?
        WHERE track_id = ?
          AND batch_id = ?;
        """,
        params=(expires_at_txt, updated_at_txt, track_id, batch_id),
        db=db,
        logger=logger,
    )


def count_active_claim_batches(
    db: str = BEETS_DB,
    logger: LoggerProtocol | None = None,
) -> int:
    logger = ensure_logger(logger, __name__)

    execute_write(
        """
        DELETE FROM track_claims
        WHERE expires_at <= datetime('now');
        """,
        db=db,
        logger=logger,
    )

    value = select_scalar(
        """
        SELECT COUNT(DISTINCT batch_id)
        FROM track_claims
        WHERE expires_at > datetime('now');
        """,
        db=db,
        logger=logger,
    )

    return int(value or 0)
