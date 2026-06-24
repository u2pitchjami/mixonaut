"""
2020-08-20 module de matching pour la key et la transposition.
"""

from __future__ import annotations

import math
import sqlite3
from collections.abc import Mapping
from typing import Final

from mixonaut.db.matching.matching_queries import get_transpositions
from mixonaut.process_matching.models.models import (
    BestCandidate,
    TranspositionDict,
)
from mixonaut.utils.config import CAMELOT_ORDER, TOLERANCE_BPM_PERCENT
from mixonaut.utils.logger import LoggerProtocol, ensure_logger

BPM_SHIFT_PENALTY = 0.1
# CAMELOT_ORDER = [f"{n}{l}" for n in range(1, 13) for l in ["a", "b"]]

KEY_TRANSITION_SCORES = {
    0: ("identique", 1.0),
    1: ("voisin tonal", 1.0),
    2: ("booster léger", 0.9),
    3: ("transition expressive", 0.8),
    5: ("coupure stylisée", 0.7),
    6: ("dissonance volontaire", 0.5),
}


def get_key_score(
    ref_key: str, candidate_key: str, logger: LoggerProtocol | None = None
) -> float:
    """
    Calculate the score of a key transition from a reference key to a candidate key.

    The score is based on the distance between the two keys in the CAMELOT order,
    with bonus points for closer transitions and penalties for greater distances.
    The score is also influenced by the specific type of transition, with different
    scores awarded for different types of transitions.
    Args:
        ref_key (str): The reference key.
        candidate_key (str): The candidate key to compare with the reference key.
        logger (LoggerProtocol | None): A logger instance, or None if no logging is desired.

    Returns:
        float: The score of the key transition.
    """
    logger = ensure_logger(logger, __name__)
    try:
        # logger.debug(
        #     f"get_key_score ref_key : {ref_key}, candidate_key : {candidate_key}"
        # )
        if ref_key == candidate_key:
            return 1.0
        ref_idx = CAMELOT_ORDER.index(ref_key)
        cand_idx = CAMELOT_ORDER.index(candidate_key)
        diff = abs(ref_idx - cand_idx) % 24
        # logger.debug(
        #     f"get_key_score ref_idx : {ref_idx}, cand_idx : {cand_idx}, diff : {diff}"
        # )
        if diff > 12:
            diff = 24 - diff
            # logger.debug(f"get_key_score diff > 12, diff : {diff}")

        for dist, (_, score) in KEY_TRANSITION_SCORES.items():
            # logger.debug(f"get key score : for dist, dist : {dist}, diff : {diff}")
            if diff == dist:
                return score
        return 0.0
    except Exception:
        logger.error(
            f"Erreur dans get_key_score: ref_key={ref_key}, cand_key={candidate_key} "
        )
        return 0.0


def calculate_key_score(
    effective_ref_key: str,
    bpm_original: float,
    bpm_transposed: float,
    transposed_key: str,
    bpm_penalty_factor: float,
    logger: LoggerProtocol | None = None,
) -> tuple[float, float, float]:
    """
    Calculate the score of a key transition from a reference key to a candidate key.

    This function first calculates the key score using the get_key_score function, then
    applies a pitch shift penalty based on the difference between the original and transposed BPMs.
    Args:
        effective_ref_key (str): The effective reference key.
        bpm_original (float): The original BPM.
        bpm_transposed (float): The transposed BPM.
        transposed_key (str): The candidate key to compare with the reference key.
        bpm_penalty_factor (float): A factor used to calculate the pitch shift penalty.
        logger (LoggerProtocol | None): A logger instance, or None if no logging is desired.

    Returns:
        tuple: A tuple containing the calculated key score, pitch shift, and penalty.
    """
    logger = ensure_logger(logger, __name__)
    key_score = get_key_score(effective_ref_key, transposed_key, logger=logger)
    pitch_shift = (
        12 * math.log2(bpm_transposed / bpm_original)
        if bpm_transposed > 0 and bpm_original > 0
        else 0.0
    )

    if abs(pitch_shift):
        penalty = bpm_penalty_factor * abs(pitch_shift)
        key_score = max(0.0, key_score - penalty)
    else:
        penalty = 0.0

    return key_score, pitch_shift, penalty


def find_best_transposition_combo(
    ref_key: str,
    target_bpm: float,  # anciennement ref_bpm
    transpo_dict: TranspositionDict,
    logger: LoggerProtocol | None = None,
) -> BestCandidate:
    """
    Explore les transpositions possibles et choisit la meilleure combo selon 'calculate_key_score', sous contrainte de
    fenêtre de BPM autour de 'target_bpm'.
    """
    logger = ensure_logger(logger, __name__)
    best: BestCandidate = {
        "score": 0.0,
        "key": None,
        "semitone": 0,
        "transposed_bpm": None,
        "pitch_shift": 0.0,
    }

    bpm_min = target_bpm * (1 - TOLERANCE_BPM_PERCENT / 100)
    bpm_max = target_bpm * (1 + TOLERANCE_BPM_PERCENT / 100)

    for i in range(-12, 13):
        k_col = _build_key_col(i)  # ex: key_plus_3 / key_minus_2 / key_0
        b_col = _build_bpm_col(i)  # ex: bpm_plus_3 / bpm_minus_2 / bpm_0

        k = transpo_dict.get(k_col)
        b = transpo_dict.get(b_col)

        if isinstance(k, str) and isinstance(b, (int, float)):
            b_float = float(b)
            if bpm_min <= b_float <= bpm_max:
                key_score, pitch_shift, penalty = calculate_key_score(
                    ref_key, target_bpm, b_float, k, BPM_SHIFT_PENALTY, logger=logger
                )
                if key_score > best["score"]:
                    best.update(
                        {
                            "score": key_score,
                            "key": k,
                            "semitone": i,
                            "transposed_bpm": b_float,
                            "pitch_shift": pitch_shift,
                        }
                    )

    return best


def build_transposition_dict(
    row: sqlite3.Row | Mapping[str, object],
) -> TranspositionDict:
    """
    Construit un dict des transpositions depuis une ligne de DB, avec des clés normalisées: key_{plus|minus|0}_N et
    bpm_{plus|minus|0}_N pour N ∈ [0..12].
    """

    # Accès 'row[col]' aussi bien pour sqlite3.Row que pour Mapping
    def _get(col: str) -> object | None:
        try:
            return row[col]
        except Exception:
            return None

    def _col(prefix: str, i: int) -> str:
        if i == 0:
            return f"{prefix}_0"
        return f"{prefix}_{'plus' if i > 0 else 'minus'}_{abs(i)}"

    result: TranspositionDict = {}

    for i in range(-12, 13):
        k_col = _col("key", i)
        b_col = _col("bpm", i)

        k_val = _get(k_col)
        b_val = _get(b_col)

        # On ne met dans le dict que ce qui est présent (évite des None non typés)
        if isinstance(k_val, str):
            result[k_col] = k_val
        if isinstance(b_val, (int, float)):
            result[b_col] = float(b_val)

    return result


PITCH_FACTOR: Final[float] = 12.0
_TOLERANCE: Final[float] = 1e-6


def _build_key_col(semitone_shift: int) -> str:
    if semitone_shift == 0:
        return "key_0"
    return f"key_{'plus' if semitone_shift > 0 else 'minus'}_{abs(semitone_shift)}"


def _build_bpm_col(semitone_shift: int) -> str:
    if semitone_shift == 0:
        return "bpm_0"
    return f"bpm_{'plus' if semitone_shift > 0 else 'minus'}_{abs(semitone_shift)}"


def get_effective_ref_key(
    track_id: int,
    ref_bpm: float,
    ref_key: str,
    target_bpm: float,
    logger: LoggerProtocol | None = None,
) -> str:
    logger = ensure_logger(logger, __name__)

    if abs(target_bpm - ref_bpm) <= _TOLERANCE:
        return ref_key

    try:
        pitch_shift = PITCH_FACTOR * math.log2(target_bpm / ref_bpm)
        semitone_shift = int(round(pitch_shift))

        transpo_row = get_transpositions(track_id, logger=logger)
        if not transpo_row:
            return ref_key

        transpo_dict = build_transposition_dict(
            transpo_row
        )  # -> dict[str, str | float]
        key_col = _build_key_col(semitone_shift)

        value = transpo_dict.get(key_col)
        if isinstance(value, str) and value:  # ✅ narrowing → str
            return value

    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("Erreur lors du calcul de la key transposée : %s", exc)

    return ref_key
