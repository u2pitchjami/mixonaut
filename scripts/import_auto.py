import argparse
from logic.auto_import import import_tracks_from_beets

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ajoute les morceaux EDM dans mix_assist.")
    args = parser.parse_args()
        
    import_tracks_from_beets()