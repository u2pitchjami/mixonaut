import argparse
import sys
from utils.logger import get_logger
from logic.auto_import import import_tracks_from_beets
logname = "Import_Auto"
logger = get_logger(logname)

if __name__ == "__main__":
    try:
        parser = argparse.ArgumentParser(description="Ajoute les morceaux EDM dans mix_assist.")
        parser.add_argument("--count", type=int, default=0, help="Nombre d'éléments à traiter (défaut: 0)")
        args = parser.parse_args()
            
        import_tracks_from_beets(count=args.count, logname=logname)
    except Exception as e:
        raise SystemExit(1)