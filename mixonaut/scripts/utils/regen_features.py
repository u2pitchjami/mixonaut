"""2025-08-20 - scripts qui regen les features essentia."""

import argparse

from mixonaut.db.analyse.essentia_queries import get_all_track_ids
from mixonaut.db.beets.db_beets_queries import get_items_columns
from mixonaut.essentia.features.recalc_features import main_recalc
from mixonaut.utils.logger import get_logger
from mixonaut.utils.safe_runner import safe_main
from mixonaut.utils.utils_div import format_nb, format_percent

logger = get_logger("Essentia_Recalc")


@safe_main
def main():
    """
    Recalculate Essentia features for multiple tracks.

    This script takes the IDs of one or more tracks and recalculates their Essentia features.
    It also allows the user to specify which fields to recalculate, and can exclude tags from the calculation.

    Args:
        track-id (int): The ID of a single track to recalculate. If not specified, all tracks will be processed.
        --recalc (nargs="+", required=True): A list of Essentia feature names to calculate.
        --no-tags (action="store_true"): Exclude tags from the calculation.

    Returns:
        None
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--track-id", type=int, required=False, help="ID du morceau")
    parser.add_argument(
        "--recalc",
        nargs="+",
        required=True,
        help="Champs à recalculer (ex: mood genre energy_level)",
    )
    parser.add_argument("--no-tags", action="store_true")

    args = parser.parse_args()

    track_ids = [args.track_id] if args.track_id else get_all_track_ids(logger=logger)
    items_columns = get_items_columns(logger=logger)
    logger.info(f"🔍 Récupération des colonnes de la table items : {items_columns}")
    logger.info(f"🔍 Démarrage du process Essentia_recalc pour : {args.recalc}")
    logger.info(
        f"🔍 Démarrage du process Essentia_recalc pour : {len(track_ids)} morceaux concernés"
    )

    errors = 0
    count = 0
    for tid in track_ids:
        count += 1
        logger.info(
            f"▶️  Analyse : {tid} - [{format_nb(count, logger=logger)}/{format_nb(len(track_ids), logger=logger)}] \
                ({format_percent(count, len(track_ids), logger=logger)})"
        )
        try:
            main_recalc(
                track_id=tid,
                recalc_fields=args.recalc,
                no_tags=args.no_tags,
                items_columns=items_columns,
                logger=logger,
            )
        except Exception:
            logger.exception(f"Erreur lors du recalcul pour le track_id {tid}")
            errors += 1

    logger.info(
        f"🏁 Traitement Essentia_recalc terminé : {len(track_ids)} morceaux traités, {errors} erreurs détectées"
    )


if __name__ == "__main__":
    main()
