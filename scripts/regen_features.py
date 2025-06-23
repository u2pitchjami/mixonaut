import argparse
from utils.utils_div import format_nb, format_percent
from essentia.recalc_features import main_recalc
from db.essentia_queries import get_all_track_ids
from utils.logger import get_logger

logname = "Essentia_Recalc"
logger = get_logger(logname)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--track-id", type=int, required=False, help="ID du morceau")
    parser.add_argument("--recalc", nargs="+", required=True, help="Champs à recalculer (ex: mood genre energy_level)")
    parser.add_argument("--no-tags", action="store_true")

    args = parser.parse_args()
    track_ids = [args.track_id] if args.track_id else get_all_track_ids()
    count = 0
    logger.info(f"🔍 Démarrage du process Essentia_recalc pour : {args.recalc}")
    logger.info(f"🔍 Démarrage du process Essentia_recalc pour : {len(track_ids)} concernées")
    for tid in track_ids:
        count += 1
        logger.info(f"▶️  Analyse : {tid} - [{format_nb(count)}/{format_nb(len(track_ids))}] ({format_percent(count, len(track_ids))})")
        main_recalc(track_id=tid, recalc_fields=args.recalc, no_tags=args.no_tags)
    logger.info("🏁 Traitement Essentia_recalc terminé")
