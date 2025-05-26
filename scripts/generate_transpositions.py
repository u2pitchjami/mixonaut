import argparse
from logic.transposition import generate_transpositions

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="génère la transposition de key.")
    parser.add_argument(
    "--count",
    type=int,
    default=0,
    help="Nombre d'éléments à traiter (défaut: 0)"
    )
    args = parser.parse_args()
    generate_transpositions(count=args.count)
