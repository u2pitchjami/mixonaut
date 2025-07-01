import argparse
from logic.transposition import generate_transpositions
from utils.utils_div import ensure_to_str, convert_path_format
from utils.logger import get_logger
import os

logger = get_logger("Generate_transposition")

if __name__ == "__main__":
    try:
        parser = argparse.ArgumentParser(description="génère la transposition de key.")
        parser.add_argument("--track-id", type=int, required=False)
        parser.add_argument("--nb-limit", type=int, default=0, help="Nombre d'éléments à traiter (défaut: 0)")
        args = parser.parse_args()
        generate_transpositions(nb_limit=args.nb_limit, track_id=args.track_id, logger=logger)
    except Exception as e:
        logger.error(f"❌ [ERROR] Erreur traitement track : {e}")
        raise SystemExit(1)
