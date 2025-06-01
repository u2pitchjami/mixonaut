import argparse
from essentia.recalc_features import main_recalc

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--track-id", type=int, required=True, help="ID du morceau")
    parser.add_argument("--recalc", nargs="+", required=True, help="Champs à recalculer (ex: mood genre energy_level)")

    args = parser.parse_args()
    main_recalc(track_id=args.track_id, recalc_fields=args.recalc)
