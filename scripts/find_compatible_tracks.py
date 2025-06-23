import argparse
from datetime import datetime
import os
from db.access import select_one, select_all
from utils.config import EXPORT_COMPATIBLE_TRACKS
from utils.logger import get_logger
from collections import defaultdict
from typing import List, Dict
import math

logname = __name__.split(".")[-1]
logger = get_logger(logname)

CAMELOT_ORDER = [f"{n}{l}" for n in range(1, 13) for l in ["a", "b"]]

KEY_TRANSITION_SCORES = {
    0: ("identique", 1.0),
    1: ("voisin tonal", 1.0),
    2: ("booster léger", 0.9),
    3: ("transition expressive", 0.8),
    5: ("coupure stylisée", 0.7),
    6: ("dissonance volontaire", 0.5),
}

PENALTY_PER_SEMITONE = 0.05
BPM_SHIFT_PENALTY = 0.2

def group_matches_by_transition_type(matches: list, ref_key: str, max_results: int = 10):
    grouped = defaultdict(list)
    logger.debug(f"group_matches_by_transition_type grouped : {grouped}")
    for m in matches:
        t_type = classify_transition_type(ref_key, m["key"])
        grouped[t_type].append(m)
        logger.debug(f"group_matches_by_transition_type m : {m}, t_type : {t_type}, grouped[t_type].append(m) : {grouped[t_type].append(m)}")

    for t_type in grouped:
        logger.debug(f"group_matches_by_transition_type t_type : {t_type}")
        grouped[t_type] = sorted(grouped[t_type], key=lambda x: x["score"], reverse=True)[:max_results]
        logger.debug(f"group_matches_by_transition_type grouped[t_type] : {len(grouped[t_type])}")

    return dict(grouped)


def get_key_score(ref_key: str, candidate_key: str) -> float:
    try:
        logger.debug(f"get_key_score ref_key : {ref_key}, candidate_key : {candidate_key}")
        if ref_key == candidate_key:
            return 1.0
        ref_idx = CAMELOT_ORDER.index(ref_key)
        cand_idx = CAMELOT_ORDER.index(candidate_key)
        diff = abs(ref_idx - cand_idx) % 24
        logger.debug(f"get_key_score ref_idx : {ref_idx}, cand_idx : {cand_idx}, diff : {diff}")
        if diff > 12:
            diff = 24 - diff
            logger.debug(f"get_key_score diff > 12, diff : {diff}")

        for dist, (_, score) in KEY_TRANSITION_SCORES.items():
            logger.debug(f"get key score : for dist, dist : {dist}, diff : {diff}")
            if diff == dist:
                return score
        return 0.4
    except:
        logger.error(f"Erreur dans get_key_score: ref_key={ref_key}, cand_key={candidate_key} → {e}")
        return 0.0

def classify_transition_type(ref_key: str, candidate_key: str) -> str:
    if ref_key == candidate_key:
        return "perfect"

    try:
        ref_idx = CAMELOT_ORDER.index(ref_key)
        cand_idx = CAMELOT_ORDER.index(candidate_key)
        diff = (cand_idx - ref_idx) % 24

        if diff == 1:
            return "+1"
        elif diff == 23:
            return "-1"
        elif candidate_key[-1] != ref_key[-1] and candidate_key[:-1] == ref_key[:-1]:
            return "scale_change"
        elif diff in [11, 13] and candidate_key[-1] != ref_key[-1]:
            return "diagonal"
        elif diff in [6, 18]:
            return "jaws"
        elif diff in [7, 17]:
            return "mood"
        else:
            return "other"
    except:
        return "unknown"

def find_compatible_tracks(
    track_id: int,
    target_bpm: float = None,
    tolerance_bpm_percent: float = 3.0,
    tolerance_energy: int = 1,
    key_match: bool = True,
    mood_match: bool = True,
    max_results: int = 15,
    grouped: bool = False,
    logname: str = logname
) -> List[Dict] | Dict[str, List[Dict]]:
    try:
        query = """
        SELECT bpm, initial_key, mood, energy_level, beat_intensity, mood_emb_1, mood_emb_2
        FROM audio_features
        WHERE id = ?
        """
        ref = select_one(query, (track_id,), logname=logname)
        if not ref:
            logger.warning(f"Track ID {track_id} introuvable dans audio_features")
            return []

        ref_bpm, ref_key, ref_mood, ref_energy, ref_beat_intensity, ref_emb1, ref_emb2 = ref
        effective_ref_key = ref_key

        if target_bpm is None:
            target_bpm = ref_bpm
        else:
            ref_pitch_shift = 12 * math.log2(target_bpm / ref_bpm)
            ref_semitone_shift = round(ref_pitch_shift)
            ref_transpo = select_one("SELECT * FROM track_transpositions WHERE id = ?", (track_id,), logname=logname)
            if ref_transpo:
                transpo_dict = dict(zip([...], ref_transpo[1:]))
                key_col = f"key_{'plus' if ref_semitone_shift > 0 else 'minus' if ref_semitone_shift < 0 else '0'}_{abs(ref_semitone_shift)}"
                if key_col in transpo_dict and transpo_dict[key_col]:
                    effective_ref_key = transpo_dict[key_col]

        bpm_min = target_bpm * (1 - tolerance_bpm_percent / 100)
        bpm_max = target_bpm * (1 + tolerance_bpm_percent / 100)
        logger.debug(f"bpm_min : {bpm_min}, bpm_max : {bpm_max}, target_bpm : {target_bpm}")
        candidates_query = """
        SELECT id, bpm, initial_key, mood, energy_level, beat_intensity, mood_emb_1, mood_emb_2
        FROM audio_features
        WHERE id != ?
        """
        candidates = select_all(candidates_query, (track_id,), logname=logname)
        logger.debug(f"candidates : {len(candidates)}")
        compatibles = []
        for row in candidates:
            cid, bpm, key, mood, energy, beat_intensity, emb1, emb2 = row

            transpo_query = "SELECT * FROM track_transpositions WHERE id = ?"
            row2 = select_one(transpo_query, (cid,), logname=logname)
            best_combo = {
                "score": 0.0,
                "key": key,
                "semitone": 0,
                "transposed_bpm": bpm,
                "pitch_shift": 0.0
            }

            if row2:
                transpo_dict = dict(zip([
                    f"key_{'plus' if i > 0 else 'minus' if i < 0 else '0'}_{abs(i)}" if i != 0 else "key_0"
                    for i in range(-12, 13)
                ] + [
                    f"bpm_{'plus' if i > 0 else 'minus' if i < 0 else '0'}_{abs(i)}" if i != 0 else "bpm_0"
                    for i in range(-12, 13)
                ], row2[1:]))

                for i in range(-12, 13):
                    k_col = f"key_{'plus' if i > 0 else 'minus' if i < 0 else '0'}_{abs(i)}" if i != 0 else "key_0"
                    b_col = f"bpm_{'plus' if i > 0 else 'minus' if i < 0 else '0'}_{abs(i)}" if i != 0 else "bpm_0"
                    k = transpo_dict.get(k_col)
                    b = transpo_dict.get(b_col)

                    if k is not None and b is not None and bpm_min <= b <= bpm_max:
                        score = get_key_score(effective_ref_key, k)
                        pitch_shift = 12 * math.log2(b / bpm) if b > 0 and bpm > 0 else 0.0
                        penalty = 0.0

                        if abs(pitch_shift) >= 1.0:
                            penalty = BPM_SHIFT_PENALTY * (abs(pitch_shift) - 1.0)
                            score -= penalty
                            score = max(score, 0.0)
                            logger.debug(f"penalty : {penalty}, BPM_SHIFT_PENALTY : {BPM_SHIFT_PENALTY}, score : {score}")

                        if score > best_combo["score"]:
                            best_combo.update({
                                "score": score,
                                "key": k,
                                "semitone": i,
                                "transposed_bpm": b,
                                "pitch_shift": pitch_shift
                            })

            elif not key_match:
                best_combo["score"] = 0.5

            if best_combo["score"] == 0:
                continue

            best_harmony_score = best_combo["score"]
            best_key = best_combo["key"]
            best_semitone = best_combo["semitone"]
            best_transposed_bpm = best_combo["transposed_bpm"]
            best_actual_pitch_shift = best_combo["pitch_shift"]
            logger.debug(f"best_key : {best_key}, best_semitone : {best_semitone}, best_transposed_bpm : {best_transposed_bpm}, best_actual_pitch_shift : {best_actual_pitch_shift}")

            score = best_harmony_score
            energy_score = 1 - abs(energy - ref_energy) / tolerance_energy
            logger.debug(f"energy : {energy}, ref_energy : {ref_energy}, tolerance_energy : {tolerance_energy}")
            score += energy_score
            logger.debug(f"score : {score}, energy_score : {energy_score}")

            beat_intensity_score = 1 - abs(beat_intensity - ref_beat_intensity) / tolerance_energy
            logger.debug(f"beat_intensity : {beat_intensity}, ref_beat_intensity : {ref_beat_intensity}, tolerance_energy : {tolerance_energy}")
            score += beat_intensity_score
            logger.debug(f"score : {score}, energy_score : {energy_score}")

            mood_score = 0.0
            if mood_match and mood == ref_mood:
                mood_score = 1.0
            elif not mood_match:
                mood_score = 0.5
            score += mood_score
            logger.debug(f"score : {score}, mood_score : {mood_score}")

            mood_sim = 0.0
            if ref_emb1 is not None and emb1 is not None:
                mood_sim = 1 - math.sqrt((ref_emb1 - emb1)**2 + (ref_emb2 - emb2)**2)
                score += mood_sim

            logger.debug(f"score : {score}, mood_sim : {mood_sim}")

            compatibles.append({
                "track_id": cid,
                "bpm": bpm,
                "key": best_key,
                "mood": mood,
                "energy_level": energy,
                "score": round(score, 3),
                "diagnostic": f"key_score={best_harmony_score:.2f}, semitones={best_semitone}, transposed_bpm={best_transposed_bpm}, bpm_target={target_bpm}, energy_delta={abs(energy - ref_energy):.2f}, mood_sim={mood_sim:.2f}, pitch_shift={best_actual_pitch_shift:.2f}"
            })
            logger.debug(f"compatibles.append : {compatibles.append}")
        if not grouped:
            compatibles.sort(key=lambda x: x["score"], reverse=True)
            return compatibles[:max_results]
        else:
            return group_matches_by_transition_type(compatibles, effective_ref_key, max_results)

    except Exception as e:
        logger.exception(f"Erreur dans find_compatible_tracks: {e}")
        return []


def enrich_matches_with_metadata(matches: list[dict]) -> list[dict]:
    for match in matches:
        row = select_one(
            "SELECT artist, album, title FROM items WHERE id = ?",
            (match["track_id"],),
            logname=logname
        )
        if row:
            match["artist"], match["album"], match["title"] = row
        else:
            match["artist"], match["album"], match["title"] = "Unknown", "Unknown", "Unknown"
    return matches

def export_matches_to_markdown(results_by_type: dict[str, list[dict]], output_dir: str = EXPORT_COMPATIBLE_TRACKS):
    logger.debug(f"output_dir : {output_dir}")
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    os.makedirs(output_dir, exist_ok=True)
    filename = f"mixonaut_matches_{timestamp}.md"
    output_path = os.path.join(output_dir, filename)

    with open(output_path, "w", encoding="utf-8") as f:
        for mix_type, matches in results_by_type.items():
            f.write(f"### 🎧 Mix Type: {mix_type}\n\n")
            f.write("| Artist | Title | Album | BPM | Key | Score | Diagnostic |\n")
            f.write("|--------|-------|-------|-----|-----|-------|------------|\n")

            enriched = enrich_matches_with_metadata(matches)

            for m in enriched:
                f.write(
                    f"| {m.get('artist', '')} | {m.get('title', '')} | {m.get('album', '')} "
                    f"| {m['bpm']} | {m['key']} | {m['score']} | {m['diagnostic']} |\n"
                )
            f.write("\n\n")

    return output_path

if __name__ == "__main__":
    try:
        parser = argparse.ArgumentParser()
        parser.add_argument("--track-id", type=int, required=True)
        parser.add_argument("--target-bpm", type=float, required=False, default=None)
        args = parser.parse_args()
        tracks = find_compatible_tracks(track_id=args.track_id, target_bpm=args.target_bpm, key_match=True, mood_match=True, grouped=True)
        export_matches_to_markdown(tracks, EXPORT_COMPATIBLE_TRACKS)
    except Exception as e:
        raise
