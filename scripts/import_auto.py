import argparse
from logic.auto_import import import_tracks_from_beets

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ajoute les morceaux EDM dans mix_assist.")
    parser.add_argument(
    "--count",
    type=int,
    default=0,
    help="Nombre d'éléments à traiter (défaut: 0)"
    )
    args = parser.parse_args()
            
    import_tracks_from_beets(count=args.count)