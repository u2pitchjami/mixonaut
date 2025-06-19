import argparse
from db.access import select_one, select_all
from utils.logger import get_logger
from typing import List, Dict
import math

logname = __name__.split(".")[-1]
logger = get_logger(logname)

CAMELOT_ORDER = [f"{n}{l}" for n in range(1, 13) for l in ["A", "B"]]

KEY_TRANSITION_SCORES = {
    0: ("identique", 1.0),
    1: ("voisin tonal", 1.0),
    2: ("booster léger", 0.9),
    3: ("transition expressive", 0.8),
    5: ("coupure stylisée", 0.7),
    6: ("dissonance volontaire", 0.5),
}

PENALTY_PER_SEMITONE = 0.05
BPM_SHIFT_PENALTY = 0.20


def get_key_score(ref_key: str, candidate_key: str) -> float:
    try:
        if ref_key == candidate_key:
            return 1.0

        ref_idx = CAMELOT_ORDER.index(ref_key)
        cand_idx = CAMELOT_ORDER.index(candidate_key)
        diff = abs(ref_idx - cand_idx) % 24
        if diff > 12:
            diff = 24 - diff

        for dist, (_, score) in KEY_TRANSITION_SCORES.items():
            if diff == dist:
                return score
        return 0.4
    except:
        return 0.0


def find_compatible_tracks(
    track_id: int,
    target_bpm: float = None,
    tolerance_bpm_percent: float = 5.0,
    tolerance_energy: int = 2,
    key_match: bool = True,
    mood_match: bool = True,
    max_results: int = 100,
    logname: str = logname
) -> List[Dict]:
    try:
        query = """
        SELECT bpm, initial_key, mood, energy_level, mood_emb_1, mood_emb_2
        FROM audio_features
        WHERE id = ?
        """
        ref = select_one(query, (track_id,), logname=logname)
        if not ref:
            logger.warning(f"Track ID {track_id} introuvable dans audio_features")
            return []

        ref_bpm, ref_key, ref_mood, ref_energy, ref_emb1, ref_emb2 = ref
        if target_bpm is None:
            target_bpm = ref_bpm

        bpm_min = target_bpm * (1 - tolerance_bpm_percent / 100)
        bpm_max = target_bpm * (1 + tolerance_bpm_percent / 100)

        candidates_query = """
        SELECT id, bpm, initial_key, mood, energy_level, mood_emb_1, mood_emb_2
        FROM audio_features
        WHERE id != ?
        """
        candidates = select_all(candidates_query, (track_id,), logname=logname)

        compatibles = []
        for row in candidates:
            cid, bpm, key, mood, energy, emb1, emb2 = row

            best_harmony_score = 0.0
            best_key = key
            best_semitone = 0
            best_transposed_bpm = bpm
            best_actual_pitch_shift = 0.0

            transpo_query = "SELECT * FROM track_transpositions WHERE id = ?"
            row2 = select_one(transpo_query, (cid,), logname=logname)
            candidate_transposed_pairs = set()

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
                    if k is not None and b is not None:
                        if bpm_min <= b <= bpm_max:
                            score = get_key_score(ref_key, k)
                            pitch_shift = 0.0
                            if b > 0 and bpm > 0:
                                pitch_shift = 12 * math.log2(b / bpm)
                                if abs(pitch_shift) >= 1.0:
                                    penalty = BPM_SHIFT_PENALTY * (abs(pitch_shift) - 1.0)
                                    score -= penalty
                                    score = max(score, 0)

                            logger.debug(f"CID={cid} k={k} b={b:.2f} score={score:.2f} pitch_shift={pitch_shift:.2f}")

                            if score > best_harmony_score:
                                best_harmony_score = score
                                best_key = k
                                best_semitone = i
                                best_transposed_bpm = b
                                best_actual_pitch_shift = pitch_shift

            elif not key_match:
                best_harmony_score = 0.5

            if best_harmony_score == 0:
                continue

            score = best_harmony_score
            energy_score = 1 - abs(energy - ref_energy) / tolerance_energy
            score += energy_score

            mood_score = 0.0
            if mood_match and mood == ref_mood:
                mood_score = 1.0
            elif not mood_match:
                mood_score = 0.5
            score += mood_score

            mood_sim = 0.0
            if ref_emb1 is not None and emb1 is not None:
                mood_sim = 1 - math.sqrt((ref_emb1 - emb1)**2 + (ref_emb2 - emb2)**2)
                score += mood_sim

            compatibles.append({
                "track_id": cid,
                "bpm": bpm,
                "key": best_key,
                "mood": mood,
                "energy_level": energy,
                "score": round(score, 3),
                "diagnostic": f"key_score={best_harmony_score:.2f}, semitones={best_semitone}, transposed_bpm={best_transposed_bpm}, bpm_target={target_bpm}, energy_delta={abs(energy - ref_energy):.2f}, mood_sim={mood_sim:.2f}, pitch_shift={best_actual_pitch_shift:.2f}"
            })

        compatibles.sort(key=lambda x: x["score"], reverse=True)
        return compatibles[:max_results]

    except Exception as e:
        logger.exception(f"Erreur dans find_compatible_tracks: {e}")
        return []


if __name__ == "__main__":
    try:
        parser = argparse.ArgumentParser()
        parser.add_argument("--track-id", type=int, required=True)
        parser.add_argument("--target-bpm", type=float, required=False)
        args = parser.parse_args()
        tracks = find_compatible_tracks(track_id=args.track_id, key_match=True, mood_match=True)
        print(f"tracks : {tracks}")
    except Exception as e:
        raise
