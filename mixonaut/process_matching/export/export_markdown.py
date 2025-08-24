"""
2025-08-20 module d'export du matching au format md.
"""

from __future__ import annotations

import os
from collections import defaultdict
from datetime import datetime
from typing import TextIO

from mixonaut.db.matching.matching_queries import enrich_matches_with_metadata
from mixonaut.process_matching.models.models import TrackMatch
from mixonaut.utils.config import CAMELOT_ORDER, EXPORT_COMPATIBLE_TRACKS
from mixonaut.utils.logger import LoggerProtocol, ensure_logger, with_child_logger

# Types d'agrégats attendus par l'export
MatchResult = list[TrackMatch] | dict[str, list[TrackMatch]]  # <— aligné au pipeline


@with_child_logger
def export_matches_to_markdown(
    results: MatchResult,
    output_dir: str = EXPORT_COMPATIBLE_TRACKS,
    logger: LoggerProtocol | None = None,
) -> str:
    """
    Exporte les résultats (flat ou groupés) en Markdown.

    Args:
        results: Liste plate de TrackMatch ou dict groupé {transition_type: [TrackMatch]}.
        output_dir: Dossier de sortie.

    Returns:
        Le chemin du fichier généré.
    """
    logger = ensure_logger(logger, __name__)
    logger.debug("output_dir : %s", output_dir)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    os.makedirs(output_dir, exist_ok=True)
    filename = f"mixonaut_matches_{timestamp}.md"
    output_path = os.path.join(output_dir, filename)

    with open(output_path, "w", encoding="utf-8") as fh:
        if isinstance(results, dict):
            # Cas groupé par type de mix
            for mix_type, matches in results.items():
                _write_mix_section(fh, mix_type, matches, logger=logger)
        elif isinstance(results, list):
            # Cas non groupé
            _write_mix_section(fh, "All Compatible Tracks", results, logger=logger)
        else:
            raise ValueError("Unsupported results format")

    logger.info("Export Markdown terminé : %s", output_path)
    return output_path


def _write_mix_section(
    file_handle: TextIO,
    mix_type: str,
    matches: list[TrackMatch],
    logger: LoggerProtocol | None = None,
) -> None:
    """
    Écrit une section markdown avec un tableau pour un groupe de matches.
    """
    logger = ensure_logger(logger, __name__)
    file_handle.write(f"### 🎧 Mix Type: {mix_type}\n\n")
    file_handle.write("| Artist | Title | Album | BPM | Key | Score | Reason |\n")
    file_handle.write("|--------|-------|-------|-----|-----|-------|--------|\n")

    # Enrichissement : ajoute artist/title/album mais ne change pas la shape de base des champs utilisés.
    enriched = enrich_matches_with_metadata(matches)

    for m in enriched:
        # Compat : certains anciens matches contenaient 'diagnostic'. On privilégie 'reason'.
        reason = m.get("reason") or m.get("diagnostic", "")
        bpm = (
            m["features"]["bpm"]
            if "features" in m
            and isinstance(m["features"], dict)
            and "bpm" in m["features"]
            else m.get("bpm", "")
        )
        file_handle.write(
            f"| {m.get('artist', '')} | {m.get('title', '')} | {m.get('album', '')} "
            f"| {bpm} | {m.get('key', '')} | {m.get('score', '')} | {reason} |\n"
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


@with_child_logger
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
