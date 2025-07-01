import argparse
from utils.utils_div import format_nb, format_percent
from essentia.recalc_features import main_recalc
from db.essentia_queries import get_all_track_ids
from db.db_beets_queries import get_items_columns
from utils.logger import get_logger

logger = get_logger("Essentia_Recalc")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--track-id", type=int, required=False, help="ID du morceau")
    parser.add_argument("--recalc", nargs="+", required=True, help="Champs à recalculer (ex: mood genre energy_level)")
    parser.add_argument("--no-tags", action="store_true")

    args = parser.parse_args()

    try:
        track_ids = [args.track_id] if args.track_id else get_all_track_ids(logger=logger)
        items_columns = get_items_columns(logger=logger)
        logger.info(f"🔍 Récupération des colonnes de la table items : {items_columns}")
        logger.info(f"🔍 Démarrage du process Essentia_recalc pour : {args.recalc}")
        logger.info(f"🔍 Démarrage du process Essentia_recalc pour : {len(track_ids)} morceaux concernés")

        errors = 0
        count = 0
        for tid in track_ids:
            count += 1
            logger.info(f"▶️  Analyse : {tid} - [{format_nb(count, logger=logger)}/{format_nb(len(track_ids), logger=logger)}] ({format_percent(count, len(track_ids), logger=logger)})")
            try:
                main_recalc(track_id=tid, recalc_fields=args.recalc, no_tags=args.no_tags, items_columns=items_columns, logger=logger)
            except Exception:
                logger.exception(f"Erreur lors du recalcul pour le track_id {tid}")
                errors += 1

        logger.info(f"🏁 Traitement Essentia_recalc terminé : {len(track_ids)} morceaux traités, {errors} erreurs détectées")

    except Exception:
        logger.exception("Erreur fatale dans le script Essentia_Recalc")

if __name__ == "__main__":
    main()
