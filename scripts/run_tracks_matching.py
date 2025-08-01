import argparse
from utils.config import EXPORT_COMPATIBLE_TRACKS
from utils.logger import get_logger
from utils.safe_runner import safe_main
from matching.find_compatible_tracks import find_compatible_tracks
from matching.export_markdown import export_matches_to_markdown

logger = get_logger("Generate_Compatible_Tracks")

@safe_main
def main(track_id, target_bpm=None, grouped=False, weights_type="standard", max_results=10):
    tracks = find_compatible_tracks(track_id=track_id, target_bpm=target_bpm, grouped=grouped, weights_type=weights_type, logger=logger, max_results=max_results)
    export_matches_to_markdown(tracks, EXPORT_COMPATIBLE_TRACKS, logger=logger)



if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--track-id", type=int, required=True)
    parser.add_argument("--target-bpm", type=float, required=False, default=None)
    parser.add_argument("--grouped", action="store_true", help="Group results by Camelot mix type.")
    parser.add_argument("--max-results", type=int, default=10, help="Maximum number of matching tracks to return.")
    parser.add_argument("--weights-type", type=str, default="standard", help="Profil de pondération à utiliser (standard, no_mood, etc.)")

    args = parser.parse_args()
    main(track_id=args.track_id, target_bpm=args.target_bpm, grouped=args.grouped, weights_type=args.weights_type, max_results=args.max_results)

