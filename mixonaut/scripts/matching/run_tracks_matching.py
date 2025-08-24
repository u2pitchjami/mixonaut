"""2025-08-20 - scripts de matching type re3."""

import argparse

from mixonaut.process_matching.export.export_markdown import export_matches_to_markdown
from mixonaut.process_matching.find_compatible_tracks import find_compatible_tracks
from mixonaut.utils.config import EXPORT_COMPATIBLE_TRACKS
from mixonaut.utils.logger import get_logger
from mixonaut.utils.safe_runner import safe_main

logger = get_logger("Generate_Compatible_Tracks")


@safe_main
def main(
    track_id: int,
    target_bpm: float | None = None,
    grouped: bool = False,
    weights_type: str = "standard",
    max_results: int = 10,
) -> None:
    """
    Generate compatible tracks for a  given track ID.

    This function takes a track ID and optional parameters to find compatible tracks.
    Compatible tracks are determined by the target BPM and grouping options.

    Parameters:
        track_id (str): The ID of the track to generate compatible tracks for.
        target_bpm (int, optional): The desired BPM for the compatible tracks. Defaults to None.
        grouped (bool, optional): Whether to group compatible tracks. Defaults to False.
        weights_type (str, optional): The type of weights to use for compatibility calculations. Defaults to "standard".
        max_results (int, optional): The maximum number of results to return. Defaults to 10.

    Returns:
        None
    """
    tracks = find_compatible_tracks(
        track_id=track_id,
        target_bpm=target_bpm,
        grouped=grouped,
        weights_type=weights_type,
        logger=logger,
        max_results=max_results,
    )
    export_matches_to_markdown(tracks, EXPORT_COMPATIBLE_TRACKS, logger=logger)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--track-id", type=int, required=True)
    parser.add_argument("--target-bpm", type=float, required=False, default=None)
    parser.add_argument(
        "--grouped", action="store_true", help="Group results by Camelot mix type."
    )
    parser.add_argument(
        "--max-results",
        type=int,
        default=10,
        help="Maximum number of matching tracks to return.",
    )
    parser.add_argument(
        "--weights-type",
        type=str,
        default="standard",
        help="Profil de pondération à utiliser (standard, no_mood, etc.)",
    )

    args = parser.parse_args()
    main(
        track_id=args.track_id,
        target_bpm=args.target_bpm,
        grouped=args.grouped,
        weights_type=args.weights_type,
        max_results=args.max_results,
    )
