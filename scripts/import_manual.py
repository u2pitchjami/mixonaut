import argparse
from logic.manual_import import import_manual_tracks

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import manuel dans mix_assist")
    parser.add_argument("--like", action="store_true", help="Mode LIKE sur les chemins")
    args = parser.parse_args()

    import_manual_tracks(like=args.like)
