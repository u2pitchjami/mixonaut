"""
2026-06-17.

modules de recalcul beat intensity bulk.
"""

from mixonaut.db.analyse.essentia_queries import get_all_audio_features
from mixonaut.essentia.features.essentia_calculate import calculate_beat_intensity
from mixonaut.utils.logger import LoggerProtocol, ensure_logger
from mixonaut.db.access import execute_many


def recalc_bulk_beat_intensity(logger: LoggerProtocol | None = None) -> None:
    """
    Recalcule le beat_intensity pour tous les morceaux dans la table audio_features.

    Args:
        logger (LoggerProtocol | None): Logger optionnel pour la journalisation.
    """
    logger = ensure_logger(logger, __name__)

    BATCH_SIZE = 5000
    rows = get_all_audio_features()
    logger.info(f"Nb de morceaux: {len(rows)}")

    updates: list[tuple[float, int]] = []

    for index, row in enumerate(rows, start=1):
        features = dict(row)
        beat_intensity = calculate_beat_intensity(features)
        logger.debug(
            "Track ID %d: beat_intensity recalculated: %.2f",
            row["id"],
            beat_intensity,
        )

        updates.append(
            (
                beat_intensity,
                row["id"],
            )
        )

        if len(updates) >= BATCH_SIZE:
            execute_many(
                """
                UPDATE audio_features
                SET beat_intensity = ?
                WHERE id = ?
                """,
                updates,
            )

            logger.info(
                "Batch commit: %d tracks",
                index,
            )

            updates.clear()

    # Dernier batch
    if updates:
        execute_many(
            """
            UPDATE audio_features
            SET beat_intensity = ?
            WHERE id = ?
            """,
            updates,
        )
