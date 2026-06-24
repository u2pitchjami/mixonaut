"""
2025-08-20 module d'export du matching au format md.
"""

from __future__ import annotations

import os
from collections import defaultdict
from datetime import datetime
from typing import TextIO

from mixonaut.process_matching.models.matching import MatchContext
from mixonaut.process_matching.models.models import (
    EnrichedTrackMatch,
    MarkdownInput,
    TrackMatch,
)
from mixonaut.utils.config import CAMELOT_ORDER, EXPORT_COMPATIBLE_TRACKS
from mixonaut.utils.logger import LoggerProtocol, ensure_logger
from mixonaut.process_matching.models.matching import MatchFilters

# Types d'agrégats attendus par l'export
MatchResult = list[TrackMatch] | dict[str, list[TrackMatch]]  # <— aligné au pipeline


def export_matches_to_markdown(
    track_id: int,
    results: MarkdownInput,
    filters: MatchFilters,
    output_dir: str = EXPORT_COMPATIBLE_TRACKS,
    logger: LoggerProtocol | None = None,
) -> str:
    """
    Exporte des EnrichedTrackMatch (plats ou groupés) en Markdown.
    """
    logger = ensure_logger(logger, __name__)
    logger.debug("output_dir : %s", output_dir)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    os.makedirs(output_dir, exist_ok=True)
    filename = f"mixonaut_matches_{timestamp}.md"
    output_path = os.path.join(output_dir, filename)

    with open(output_path, "w", encoding="utf-8") as fh:
        if isinstance(results, dict):
            for mix_type, matches in results.items():
                _write_mix_section(
                    fh,
                    mix_type,
                    filters,
                    matches,
                    logger=logger,
                )
        elif isinstance(results, list):
            _write_mix_section(
                fh,
                "All Compatible Tracks",
                filters,
                results,
                logger=logger,
            )
        else:
            raise TypeError("Unsupported markdown input type")

    logger.info("Export Markdown terminé : %s", output_path)
    return output_path


def _write_mix_section(
    file_handle: TextIO,
    mix_type: str,
    filters: MatchFilters,
    matches: list[EnrichedTrackMatch],
    logger: LoggerProtocol | None = None,
) -> None:
    """
    Écrit une section markdown pour un groupe de tracks enrichies.
    """
    logger = ensure_logger(logger, __name__)

    file_handle.write(f"### 🎧 Mix Type: {mix_type}\n")
    file_handle.write(f"### 🪪 Filters: {filters}\n\n")
    file_handle.write(
        "| Artist | Title | Album | BPM | Key | Beat Intensity | Score | Reason |\n"
    )
    file_handle.write(
        "|--------|-------|-------|-----|-----|----------------|--------|-------|\n"
    )

    for m in matches:
        reason = m.get("reason", "")
        bpm = m["features"]["bpm"]
        key = m["features"]["key"]
        bi = m["features"]["beat_intensity"]

        file_handle.write(
            f"| {m.get('artist', '')} "
            f"| {m.get('title', '')} "
            f"| {m.get('album', '')} "
            f"| {bpm:.1f} "
            f"| {key} "
            f"| {bi} "
            f"| {m.get('score', 0.0):.3f} "
            f"| {reason} |\n"
        )

    file_handle.write("\n\n")


def classify_transition_type(ref_key: str, candidate_key: str) -> str:
    """
    Classifie le type de transition entre deux clés Camelot.
    """
    if ref_key == candidate_key:
        return "Perfect"

    try:
        ref_idx = CAMELOT_ORDER.index(ref_key)
        cand_idx = CAMELOT_ORDER.index(candidate_key)
        diff = (cand_idx - ref_idx) % 24

        if diff == 1:
            return "Dominant"
        if diff == 23:
            return "Subdominant"
        if candidate_key[-1] != ref_key[-1] and candidate_key[:-1] == ref_key[:-1]:
            return "Scale_change"
        if diff in (11, 13) and candidate_key[-1] != ref_key[-1]:
            return "Diagonal"
        if diff in (6, 18):
            return "Jaws"
        if diff in (7, 17):
            return "Mood_shifter"
        return "other"
    except Exception:  # pylint: disable=broad-except
        return "unknown"


def group_matches_by_transition_type(
    matches: list[TrackMatch],
    ref_key: str,
    max_results: int = 10,
    logger: LoggerProtocol | None = None,
) -> dict[str, list[TrackMatch]]:
    """
    Regroupe les matches par type de transition (clé égale, relative, voisine, etc.) et tronque chaque groupe à
    `max_results`, trié par score décroissant.
    """
    logger = ensure_logger(logger, __name__)
    grouped: defaultdict[str, list[TrackMatch]] = defaultdict(list)

    for m in matches:
        t_type = classify_transition_type(ref_key, m["key"])
        grouped[t_type].append(m)

    for t_type, items in grouped.items():
        grouped[t_type] = sorted(items, key=lambda x: x["score"], reverse=True)[
            :max_results
        ]

    return dict(grouped)


def group_enriched_matches_by_transition_type(
    *,
    matches: list[EnrichedTrackMatch],
    context: MatchContext,
    max_results: int = 10,
    logger: LoggerProtocol | None = None,
) -> dict[str, list[EnrichedTrackMatch]]:
    grouped: defaultdict[str, list[EnrichedTrackMatch]] = defaultdict(list)

    for m in matches:
        transition = classify_transition_type(
            context.effective_ref_key,
            m["features"]["key"],
        )
        grouped[transition].append(m)

    for t_type, items in grouped.items():
        grouped[t_type] = sorted(
            items,
            key=lambda x: x["score"],
            reverse=True,
        )[:max_results]

    return dict(grouped)
