"""
2026-06-17.

modules de recalcul beat intensity bulk.
"""

from mixonaut.db.analyse.madmom_queries import (
    get_all_madmom_features_for_bulk,
    save_madmom_enrichment_batch,
)
from mixonaut.madmom.features.madmom_enrich import enrich_features_madmom
from mixonaut.utils.logger import LoggerProtocol, ensure_logger
from typing import cast
from mixonaut.utils.config import MADMOM_ANALYSIS_VERSION


def recalc_bulk_madmom_enrichment(logger: LoggerProtocol | None = None) -> None:
    """
    Recalcule les features dérivées Madmom pour tous les morceaux disposant déjà des données Madmom brutes.
    """
    logger = ensure_logger(logger, __name__)

    batch_size = 5000
    rows = get_all_madmom_features_for_bulk()

    logger.info("Nb de morceaux Madmom à enrichir: %d", len(rows))

    updates: list[
        tuple[
            float | None,
            float | None,
            float | None,
            float | None,
            float | None,
            str,
            int,
        ]
    ] = []

    for index, row in enumerate(rows, start=1):
        try:
            features = dict(row)

            enriched = enrich_features_madmom(
                track_features=features,
                duration=features.get("duration"),
                logger=logger,
            )

            updates.append(
                (
                    cast(float | None, enriched.get("beats_per_second")),
                    cast(float | None, enriched.get("onsets_per_second")),
                    cast(float | None, enriched.get("downbeats_per_second")),
                    cast(float | None, enriched.get("rhythm_stability")),
                    cast(float | None, enriched.get("rhythm_intensity")),
                    str(enriched.get("analysis_version") or MADMOM_ANALYSIS_VERSION),
                    int(row["id"]),
                )
            )

            logger.debug(
                "Track ID %d: Madmom enrichment recalculated",
                row["id"],
            )

            if len(updates) >= batch_size:
                save_madmom_enrichment_batch(updates)
                logger.info("Batch commit: %d tracks", index)
                updates.clear()

        except Exception:
            logger.exception(
                "Erreur recalcul enrichissement Madmom pour track ID %s",
                row["id"],
            )

    if updates:
        save_madmom_enrichment_batch(updates)
        logger.info("Final batch commit: %d tracks", len(updates))
