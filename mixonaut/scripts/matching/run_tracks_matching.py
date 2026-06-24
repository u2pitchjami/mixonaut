"""2025-08-20 - scripts de matching type re3."""

import argparse

from mixonaut.db.matching.matching_queries import enrich_matches
from mixonaut.process_matching.export.export_markdown import (
    export_matches_to_markdown,
    group_enriched_matches_by_transition_type,
)
from mixonaut.process_matching.export.playlist_m3u import (
    build_playlist_filename,
    generate_m3u_from_matches,
)
from mixonaut.process_matching.find_compatible_tracks import (
    build_match_context,
    find_compatible_tracks,
)
from mixonaut.utils.config import PLAYLISTS_PATH
from mixonaut.utils.logger import get_logger
from mixonaut.utils.safe_runner import safe_main
from mixonaut.process_matching.models.matching import MatchFilters
from mixonaut.process_matching.models.models import EnrichedTrackMatch

logger = get_logger("Generate_Compatible_Tracks")


@safe_main
def main(
    filters: MatchFilters,
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
        genre (str, optional): The genre to filter compatible tracks. Defaults to "all".
        artist (str, optional): The artist to filter compatible tracks. Defaults to None.
        label (str, optional): The label to filter compatible tracks. Defaults to None.
        year_min (int, optional): The minimum year to filter compatible tracks. Defaults to None.
        year_max (int, optional): The maximum year to filter compatible tracks. Defaults to None.
        include_live (bool, optional): Whether to include live tracks. Defaults to False.

    Returns:
        None
    """
    context = build_match_context(
        track_id=filters.id_base,
        target_bpm=filters.target_bpm,
        interactive=True,
        logger=logger,
    )

    results = find_compatible_tracks(
        context=context,
        filters=filters,
        logger=logger,
    )

    filename = build_playlist_filename(
        track_id=filters.id_base,
        target_bpm=filters.target_bpm,
    )

    playlist_path = PLAYLISTS_PATH / filename
    logger.info("Generating M3U playlist: %s", playlist_path)
    logger.debug(
        "PLAYLIST DEBUG | PLAYLISTS_PATH=%r (%s) | playlist_path=%r (%s)",
        PLAYLISTS_PATH,
        type(PLAYLISTS_PATH),
        playlist_path,
        type(playlist_path),
    )

    enriched = enrich_matches(results, logger=logger)

    for m in enriched[:3]:
        logger.debug(
            "ENRICHED | id=%s | artist=%s | title=%s | album=%s | path=%s",
            m["id"],
            m["artist"],
            m["title"],
            m["album"],
            m["path"],
        )

    if filters.grouped:
        grouped_matches = group_enriched_matches_by_transition_type(
            matches=enriched,
            context=context,
            max_results=filters.max_results,
            logger=logger,
        )
        export_matches_to_markdown(
            filters.id_base, grouped_matches, filters, logger=logger
        )

        matches: list[EnrichedTrackMatch] = [
            match
            for group_matches in grouped_matches.values()
            for match in group_matches
        ]

        generate_m3u_from_matches(
            matches=matches,
            playlist_path=playlist_path,
            logger=logger,
        )
    else:
        export_matches_to_markdown(
            filters.id_base, enriched[: filters.max_results], filters, logger=logger
        )

        # playlist toujours plate
        generate_m3u_from_matches(
            matches=enriched[: filters.max_results],
            playlist_path=playlist_path,
            logger=logger,
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--track-id",
        type=int,
        required=True,
    )

    parser.add_argument(
        "--target-bpm",
        type=float,
        required=False,
        default=None,
    )

    parser.add_argument(
        "--grouped",
        action="store_true",
        help="Group results by Camelot mix type.",
    )

    parser.add_argument(
        "--max-results",
        type=int,
        default=50,
        help="Maximum number of matching tracks to return.",
    )

    parser.add_argument(
        "--weights-type",
        type=str,
        default="standard",
        help="Profil de pondération à utiliser (standard, no_mood, etc.)",
    )

    parser.add_argument(
        "--genre",
        type=str,
        default="all",
        help=(
            "Genre BPM range utilisé pour filtrer les résultats "
            "(ex: 'house', 'deep_house', 'ambient')."
        ),
    )

    parser.add_argument(
        "--artist",
        type=str,
        default=None,
        help="Filtrer les résultats sur un artiste spécifique.",
    )

    parser.add_argument(
        "--label",
        type=str,
        default=None,
        help="Filtrer les résultats sur un label spécifique.",
    )

    parser.add_argument(
        "--year-min",
        type=int,
        default=None,
        help="Année minimale des tracks candidates.",
    )

    parser.add_argument(
        "--year-max",
        type=int,
        default=None,
        help="Année maximale des tracks candidates.",
    )

    parser.add_argument(
        "--include-live",
        action="store_true",
        default=False,
        help="Inclure les albums live et broadcast.",
    )

    args = parser.parse_args()
    filters = MatchFilters(
        id_base=args.track_id,
        target_bpm=args.target_bpm,
        weights_type=args.weights_type,
        max_results=args.max_results,
        genre=args.genre,
        artist=args.artist,
        label=args.label,
        year_min=args.year_min,
        year_max=args.year_max,
        include_live=args.include_live,
        grouped=args.grouped,
    )

    main(filters=filters)
