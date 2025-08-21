"""
2025-08-20 module d'export du matching au format md.
"""

import os
from collections import defaultdict
from datetime import datetime

from mixonaut.db.matching.matching_queries import enrich_matches_with_metadata
from mixonaut.utils.config import CAMELOT_ORDER, EXPORT_COMPATIBLE_TRACKS
from mixonaut.utils.logger import LoggerProtocol, ensure_logger, with_child_logger

# CAMELOT_ORDER = [f"{n}{l}" for n in range(1, 13) for l in ["a", "b"]]


@with_child_logger
def export_matches_to_markdown(
    results_by_type: dict[str, list[dict]] | list[dict],
    output_dir: str = EXPORT_COMPATIBLE_TRACKS,
    logger: LoggerProtocol | None = None,
) -> str:
    """
    Exports matches to a markdown file.

    Args:
        results_by_type (dict[str, list[dict]] | list[dict]): The matching results.
        output_dir (str): The directory where the output will be written. Defaults to EXPORT_COMPATIBLE_TRACKS.
        logger (LoggerProtocol | None): A logger instance for logging purposes. Defaults to None.

    Returns:
        str: The path of the generated markdown file.
    """
    logger = ensure_logger(logger, __name__)
    logger.debug(f"output_dir : {output_dir}")
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    os.makedirs(output_dir, exist_ok=True)
    filename = f"mixonaut_matches_{timestamp}.md"
    output_path = os.path.join(output_dir, filename)

    with open(output_path, "w", encoding="utf-8") as f:
        if isinstance(results_by_type, dict):
            # Cas groupé par type de mix
            for mix_type, matches in results_by_type.items():
                _write_mix_section(f, mix_type, matches)
        elif isinstance(results_by_type, list):
            # Cas non groupé
            _write_mix_section(f, "All Compatible Tracks", results_by_type)
        else:
            raise ValueError("Unsupported results format")

    return output_path


def _write_mix_section(file_handle, mix_type: str, matches: list[dict]):
    file_handle.write(f"### 🎧 Mix Type: {mix_type}\n\n")
    file_handle.write("| Artist | Title | Album | BPM | Key | Score | Diagnostic |\n")
    file_handle.write("|--------|-------|-------|-----|-----|-------|------------|\n")

    enriched = enrich_matches_with_metadata(matches)

    for m in enriched:
        file_handle.write(
            f"| {m.get('artist', '')} | {m.get('title', '')} | {m.get('album', '')} "
            f"| {m['bpm']} | {m['key']} | {m['score']} | {m['diagnostic']} |\n"
        )
    file_handle.write("\n\n")


def classify_transition_type(ref_key: str, candidate_key: str) -> str:
    """
    Classify the transition type between two keys in CAMELOT_ORDER.

    Args:
        ref_key (str): The reference key.
        candidate_key (str): The candidate key to compare with the reference key.

    Returns:
        str: The classification of the transition type, one of 'Perfect', 'Dominant', 'Subdominant',
             'Scale_change', 'Diagonal', 'Jaws', 'Mood_shifter', or 'other'.
    """
    if ref_key == candidate_key:
        return "Perfect"

    try:
        ref_idx = CAMELOT_ORDER.index(ref_key)
        cand_idx = CAMELOT_ORDER.index(candidate_key)
        diff = (cand_idx - ref_idx) % 24

        if diff == 1:
            return "Dominant"
        elif diff == 23:
            return "Subdominant"
        elif candidate_key[-1] != ref_key[-1] and candidate_key[:-1] == ref_key[:-1]:
            return "Scale_change"
        elif diff in [11, 13] and candidate_key[-1] != ref_key[-1]:
            return "Diagonal"
        elif diff in [6, 18]:
            return "Jaws"
        elif diff in [7, 17]:
            return "Mood_shifter"
        else:
            return "other"
    except:
        return "unknown"


@with_child_logger
def group_matches_by_transition_type(
    matches: list,
    ref_key: str,
    max_results: int = 10,
    logger: LoggerProtocol | None = None,
) -> dict[str, list]:
    """
    Group a list of matches by transition type.

    The transition type is determined by comparing the reference key to each match's key.
    If the keys are the same, it's considered "Perfect". Otherwise, the transition type
    is determined using the CAMELOT_ORDER list.

    Args:
        matches (list): A list of dictionaries representing the matches.
        ref_key (str): The reference key to compare with the match keys.
        max_results (int): The maximum number of matches to return for each transition type. Defaults to 10.
        logger (LoggerProtocol | None): An optional logger instance.

    Returns:
        dict[str, list]: A dictionary mapping transition types to lists of matching dictionaries.
    """
    logger = ensure_logger(logger, __name__)
    grouped: defaultdict[str, list] = defaultdict(list)
    logger.debug(f"group_matches_by_transition_type grouped : {grouped}")
    for m in matches:
        t_type = classify_transition_type(ref_key, m["key"])
        grouped[t_type].append(m)
        logger.debug(
            f"group_matches_by_transition_type m : {m}, t_type : {t_type}, grouped[t_type] : {grouped[t_type]}"
        )

    for t_type in grouped:
        logger.debug(f"group_matches_by_transition_type t_type : {t_type}")
        grouped[t_type] = sorted(
            grouped[t_type], key=lambda x: x["score"], reverse=True
        )[:max_results]
        logger.debug(
            f"group_matches_by_transition_type grouped[t_type] : {len(grouped[t_type])}"
        )

    return dict(grouped)
