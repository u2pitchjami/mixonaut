from datetime import datetime
import os
from collections import defaultdict
from db.access import select_one, select_all
from db.matching_queries import enrich_matches_with_metadata
from utils.config import EXPORT_COMPATIBLE_TRACKS, CAMELOT_ORDER
from utils.logger import get_logger

logname = __name__.split(".")[-1]
logger = get_logger(logname)

#CAMELOT_ORDER = [f"{n}{l}" for n in range(1, 13) for l in ["a", "b"]]

def export_matches_to_markdown(results_by_type: dict[str, list[dict]] | list[dict], output_dir: str = EXPORT_COMPATIBLE_TRACKS):
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
    
def group_matches_by_transition_type(matches: list, ref_key: str, max_results: int = 10):
    grouped = defaultdict(list)
    logger.debug(f"group_matches_by_transition_type grouped : {grouped}")
    for m in matches:
        t_type = classify_transition_type(ref_key, m["key"])
        grouped[t_type].append(m)
        logger.debug(f"group_matches_by_transition_type m : {m}, t_type : {t_type}, grouped[t_type] : {grouped[t_type]}")

    for t_type in grouped:
        logger.debug(f"group_matches_by_transition_type t_type : {t_type}")
        grouped[t_type] = sorted(grouped[t_type], key=lambda x: x["score"], reverse=True)[:max_results]
        logger.debug(f"group_matches_by_transition_type grouped[t_type] : {len(grouped[t_type])}")

    return dict(grouped)