"""2025-08-20 - scripts qui regen les features essentia."""

from mixonaut.utils.logger import get_logger
from mixonaut.utils.safe_runner import safe_main
from mixonaut.essentia.features.recalc_bulk_bi import recalc_bulk_beat_intensity

logger = get_logger("Beat Intensity Recalc Bulk")


@safe_main
def main() -> None:
    """
    Recalculate Beat Intensity features for multiple tracks.

    This script takes the IDs of one or more tracks and recalculates their Beat Intensity features.
    It also allows the user to specify which fields to recalculate, and can exclude tags from the calculation.

    Args:
        track-id (int): The ID of a single track to recalculate. If not specified, all tracks will be processed.
        --recalc (nargs="+", required=True): A list of Beat Intensity feature names to calculate.
        --no-tags (action="store_true"): Exclude tags from the calculation.

    Returns:
        None
    """
    # parser = argparse.ArgumentParser()
    # parser.add_argument("--track-id", type=int, required=False, help="ID du morceau")
    # parser.add_argument(
    #     "--recalc",
    #     nargs="+",
    #     required=True,
    #     help="Champs à recalculer (ex: mood genre energy_level)",
    # )
    # parser.add_argument("--no-tags", action="store_true")

    # args = parser.parse_args()

    # track_ids = [args.track_id] if args.track_id else get_all_track_ids(logger=logger)
    # items_columns = get_items_columns(logger=logger)
    # logger.info(f"🔍 Récupération des colonnes de la table items : {items_columns}")
    logger.info("🔍 Démarrage du process Beat Intensity Recalc Bulk")
    # logger.info(
    #     f"🔍 Démarrage du process Beat Intensity Recalc pour : {len(track_ids)} morceaux concernés"
    # )

    # errors = 0
    # count = 0
    # for tid in track_ids:
    #     count += 1
    #     logger.info(
    #         f"▶️  Analyse : {tid} - [{format_nb(count, logger=logger)}/{format_nb(len(track_ids), logger=logger)}] \
    #             ({format_percent(count, len(track_ids), logger=logger)})"
    # )
    try:
        recalc_bulk_beat_intensity(
            logger=logger,
        )
    except Exception:
        logger.exception("Erreur lors du recalcul")

    logger.info("🏁 Traitement Beat Intensity Recalc terminé")


if __name__ == "__main__":
    main()
