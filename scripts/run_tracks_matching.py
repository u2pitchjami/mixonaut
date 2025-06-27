import argparse
from utils.config import EXPORT_COMPATIBLE_TRACKS
from utils.logger import get_logger
from matching.find_compatible_tracks import find_compatible_tracks
from matching.export_markdown import export_matches_to_markdown

logname = "find_compatible_tracks"
logger = get_logger(logname)

if __name__ == "__main__":
    try:
        parser = argparse.ArgumentParser()
        parser.add_argument("--track-id", type=int, required=True)
        parser.add_argument("--target-bpm", type=float, required=False, default=None)
        args = parser.parse_args()
        tracks = find_compatible_tracks(track_id=args.track_id, target_bpm=args.target_bpm, key_match=True, mood_match=True, grouped=False)
        export_matches_to_markdown(tracks, EXPORT_COMPATIBLE_TRACKS)
    except Exception as e:
        raise
