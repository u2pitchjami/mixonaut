import argparse
from essentia.recalc_features import main_recalc
from db.essentia_queries import get_all_track_ids

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--track-id", type=int, required=False, help="ID du morceau")
    parser.add_argument("--recalc", nargs="+", required=True, help="Champs à recalculer (ex: mood genre energy_level)")

    args = parser.parse_args()
    track_ids = [args.track_id] if args.track_id else get_all_track_ids()

    for tid in track_ids:
        main_recalc(track_id=tid, recalc_fields=args.recalc)
