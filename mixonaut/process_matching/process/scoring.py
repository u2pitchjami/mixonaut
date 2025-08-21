"""
2020-08-20 module hub de scoring pour le matching.
"""

from mixonaut.db.matching.matching_queries import get_transpositions
from mixonaut.process_matching.param.weights import get_weights
from mixonaut.process_matching.process.key_process import (
    build_transposition_dict,
    find_best_transposition_combo,
)
from mixonaut.process_matching.process.others_process import (
    calculate_beat_intensity_score,
    calculate_bpm_similarity,
    calculate_duration_similarity,
    calculate_genre_sim_score,
    calculate_mood_sim_score,
)
from mixonaut.utils.logger import LoggerProtocol, ensure_logger, with_child_logger


def compute_candidate_scores(
    ref_bpm: float,
    ref_duration: float,
    ref_beat_intensity: int,
    ref_mood_emb1: float,
    ref_mood_emb2: float,
    ref_genre_emb1: float,
    ref_genre_emb2: float,
    candidate: dict,
    best_combo: dict,
) -> dict:
    """
    Compute the score of a candidate in comparison to a reference.

    Args:
        ref_bpm (float): The BPM of the reference audio.
        ref_duration (float): The duration of the reference audio.
        ref_beat_intensity (int): The beat intensity of the reference audio.
        ref_mood_emb1 (float): The mood embedding 1 of the reference audio.
        ref_mood_emb2 (float): The mood embedding 2 of the reference audio.
        ref_genre_emb1 (float): The genre embedding 1 of the reference audio.
        ref_genre_emb2 (float): The genre embedding 2 of the reference audio.
        candidate (dict): The dictionary containing the candidate's metadata.
            Should include bpm, duration, beat_intensity, mood_emb1, mood_emb2,
            and genre_emb1.
        best_combo (dict): The dictionary containing the best combination of
            transpositions.
    Returns:
        dict: A dictionary containing the key, BPM similarity, genre similarity,
            duration similarity, beat intensity score, and mood similarity score.
    """
    return {
        "key": best_combo["score"],
        "bpm_sim": calculate_bpm_similarity(
            ref_bpm=ref_bpm, candidate_bpm=candidate["bpm"]
        ),
        "genre_sim": calculate_genre_sim_score(
            ref_emb1=ref_genre_emb1,
            ref_emb2=ref_genre_emb2,
            emb1=candidate["genre_emb1"],
            emb2=candidate["genre_emb2"],
        ),
        "duration_sim": calculate_duration_similarity(
            ref_duration=ref_duration, candidate_duration=candidate["duration"]
        ),
        "beat_intensity": calculate_beat_intensity_score(
            candidate["beat_intensity"], ref_beat_intensity
        ),
        "mood_sim": calculate_mood_sim_score(
            ref_emb1=ref_mood_emb1,
            ref_emb2=ref_mood_emb2,
            emb1=candidate["mood_emb1"],
            emb2=candidate["mood_emb2"],
        ),
    }


def compute_total_score(scores: dict, weights: dict) -> float:
    """
    Compute the total score by multiplying each score with its corresponding weight and summing them up.

    Args:
        scores (dict): A dictionary containing the scores for different parameters.
        weights (dict): A dictionary containing the weights for different parameters.

    Returns:
        float: The total score.
    """
    return sum(scores[k] * weights[k] for k in scores if k in weights)


@with_child_logger
def get_compatible_candidates(
    candidates: list[tuple],
    ref_bpm: float,
    ref_duration: float,
    ref_beat_intensity: int,
    ref_mood_emb1: float,
    ref_mood_emb2: float,
    ref_genre_emb1: float,
    ref_genre_emb2: float,
    effective_ref_key: str,
    target_bpm: float,
    weights_type: str,
    logger: LoggerProtocol | None = None,
) -> list[dict]:
    """
    Computes the scores of all candidates by matching them with a reference track.

    Parameters:
    candidates (list[tuple]): List of tuples containing candidate track information.
    ref_bpm (float): Reference BPM.
    ref_duration (float): Reference duration.
    ref_beat_intensity (int): Reference beat intensity.
    ref_mood_emb1 (float): First embedding of reference mood.
    ref_mood_emb2 (float): Second embedding of reference mood.
    ref_genre_emb1 (float): First embedding of reference genre.
    ref_genre_emb2 (float): Second embedding of reference genre.
    effective_ref_key (str): Effective key of the reference track.
    target_bpm (float): Target BPM.
    weights_type (str): Type of weights to use.
    logger (LoggerProtocol | None): Logger instance. Defaults to None.

    Returns:
    list[dict]: List of dictionaries containing compatible candidate information.
    """
    logger = ensure_logger(logger, __name__)
    weights = get_weights(weights_type)
    compatibles = []

    for row in candidates:
        (
            cid,
            bpm,
            key,
            beat_intensity,
            mood_emb1,
            mood_emb2,
            genre_emb1,
            genre_emb2,
            duration,
        ) = row
        transpo_row = get_transpositions(cid, logger=logger)

        best_combo = {
            "score": 0.0,
            "key": key,
            "semitone": 0,
            "transposed_bpm": bpm,
            "pitch_shift": 0.0,
        }

        if transpo_row:
            transpo_dict = build_transposition_dict(transpo_row)
            best_combo = find_best_transposition_combo(
                effective_ref_key, target_bpm, transpo_dict, logger=logger
            )

        if best_combo["score"] == 0:
            continue

        candidate_data = {
            "bpm": bpm,
            "beat_intensity": beat_intensity,
            "mood_emb1": mood_emb1,
            "mood_emb2": mood_emb2,
            "genre_emb1": genre_emb1,
            "genre_emb2": genre_emb2,
            "duration": duration,
        }

        scores = compute_candidate_scores(
            ref_bpm,
            ref_duration,
            ref_beat_intensity,
            ref_mood_emb1,
            ref_mood_emb2,
            ref_genre_emb1,
            ref_genre_emb2,
            candidate_data,
            best_combo,
        )
        total_score = compute_total_score(scores, weights)

        compatibles.append(
            {
                "track_id": cid,
                "bpm": bpm,
                "key": best_combo["key"],
                "mood": row[4],  # mood = mood_emb1 (?)
                "beat_intensity": beat_intensity,
                "score": round(total_score, 3),
                "diagnostic": ", ".join([f"{k}_score={scores[k]:.2f}" for k in scores]),
            }
        )

    return compatibles
