from utils.config import CAMELOT_ORDER, TOLERANCE_BPM_PERCENT
from db.matching_queries import get_transpositions
from collections import defaultdict
import math
from utils.logger import get_logger, with_child_logger

BPM_SHIFT_PENALTY = 0.1
#CAMELOT_ORDER = [f"{n}{l}" for n in range(1, 13) for l in ["a", "b"]]

KEY_TRANSITION_SCORES = {
    0: ("identique", 1.0),
    1: ("voisin tonal", 1.0),
    2: ("booster léger", 0.9),
    3: ("transition expressive", 0.8),
    5: ("coupure stylisée", 0.7),
    6: ("dissonance volontaire", 0.5),
}

@with_child_logger 
def get_key_score(ref_key: str, candidate_key: str, logger: str = logger) -> float:
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
        return 0.0
    except:
        logger.error(f"Erreur dans get_key_score: ref_key={ref_key}, cand_key={candidate_key} ")
        return 0.0
@with_child_logger
def calculate_key_score(effective_ref_key, bpm_original, bpm_transposed, transposed_key, bpm_penalty_factor, logger=None) -> tuple:
    key_score = get_key_score(effective_ref_key, transposed_key, logger=logger)
    pitch_shift = 12 * math.log2(bpm_transposed / bpm_original) if bpm_transposed > 0 and bpm_original > 0 else 0.0

    if abs(pitch_shift):
        penalty = bpm_penalty_factor * abs(pitch_shift)
        key_score = max(0.0, key_score - penalty)       
    else:
        penalty = 0.0

    return key_score, pitch_shift, penalty

@with_child_logger
def find_best_transposition_combo(ref_key: str, ref_bpm: float, transpo_dict: dict, logger: str = None) -> dict:
    best = {
        "score": 0.0,
        "key": None,
        "semitone": 0,
        "transposed_bpm": None,
        "pitch_shift": 0.0
    }
    bpm_min = ref_bpm * (1 - TOLERANCE_BPM_PERCENT / 100)
    bpm_max = ref_bpm * (1 + TOLERANCE_BPM_PERCENT / 100)
    for i in range(-12, 13):
        k_col = f"key_{'plus' if i > 0 else 'minus' if i < 0 else '0'}_{abs(i)}" if i != 0 else "key_0"
        b_col = f"bpm_{'plus' if i > 0 else 'minus' if i < 0 else '0'}_{abs(i)}" if i != 0 else "bpm_0"
        k = transpo_dict.get(k_col)
        b = transpo_dict.get(b_col)

        if k is not None and b is not None and bpm_min <= b <= bpm_max:
            key_score, pitch_shift, penalty = calculate_key_score(ref_key, ref_bpm, b, k, BPM_SHIFT_PENALTY, logger=logger)
            if key_score > best["score"]:
                best.update({
                    "score": key_score,
                    "key": k,
                    "semitone": i,
                    "transposed_bpm": b,
                    "pitch_shift": pitch_shift
                })
    return best

def build_transposition_dict(row: tuple) -> dict:
    key_cols = [f"key_{'plus' if i > 0 else 'minus' if i < 0 else '0'}_{abs(i)}" if i != 0 else "key_0" for i in range(-12, 13)]
    bpm_cols = [f"bpm_{'plus' if i > 0 else 'minus' if i < 0 else '0'}_{abs(i)}" if i != 0 else "bpm_0" for i in range(-12, 13)]
    return dict(zip(key_cols + bpm_cols, row[1:]))

@with_child_logger
def get_effective_ref_key(track_id: int, ref_bpm: float, ref_key: str, target_bpm: float, logger: str = None) -> str:
    if target_bpm == ref_bpm:
        return ref_key
    try:
        ref_pitch_shift = 12 * math.log2(target_bpm / ref_bpm)
        ref_semitone_shift = round(ref_pitch_shift)
        ref_transpo = get_transpositions(track_id, logger=logger)
        if ref_transpo:
            transpo_dict = build_transposition_dict(ref_transpo)
            key_col = f"key_{'plus' if ref_semitone_shift > 0 else 'minus' if ref_semitone_shift < 0 else '0'}_{abs(ref_semitone_shift)}"
            if key_col in transpo_dict and transpo_dict[key_col]:
                return transpo_dict[key_col]
    except Exception as e:
        logger.warning(f"Erreur lors du calcul de la key transposée : {e}")

    return ref_key  # fallback si problème