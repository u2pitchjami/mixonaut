from utils.logger import get_logger, with_child_logger
from matching.weights import get_weights
from db.matching_queries import get_transpositions
from matching.key_process import build_transposition_dict, find_best_transposition_combo
from matching.others_process import calculate_mood_sim_score, calculate_bpm_similarity, calculate_beat_intensity_score, calculate_duration_similarity, calculate_genre_sim_score

def compute_candidate_scores(
    ref_bpm: float,
    ref_duration: float,
    ref_beat_intensity: int,
    ref_mood_emb1: float,
    ref_mood_emb2: float,
    ref_genre_emb1: float,
    ref_genre_emb2: float,
    candidate: dict,
    best_combo: dict
) -> dict:
    return {
        "key": best_combo["score"],
        "bpm_sim": calculate_bpm_similarity(ref_bpm=ref_bpm, candidate_bpm=candidate["bpm"]),
        "genre_sim": calculate_genre_sim_score(ref_emb1=ref_genre_emb1, ref_emb2=ref_genre_emb2, emb1=candidate["genre_emb1"], emb2=candidate["genre_emb2"]),
        "duration_sim": calculate_duration_similarity(ref_duration=ref_duration, candidate_duration=candidate["duration"]),
        "beat_intensity": calculate_beat_intensity_score(candidate["beat_intensity"], ref_beat_intensity),
        "mood_sim": calculate_mood_sim_score(ref_emb1=ref_mood_emb1, ref_emb2=ref_mood_emb2, emb1=candidate["mood_emb1"], emb2=candidate["mood_emb2"])
    }

def compute_total_score(scores: dict, weights: dict) -> float:
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
    logger: str = logger
) -> list[dict]:
    weights = get_weights(weights_type)
    compatibles = []

    for row in candidates:
        cid, bpm, key, beat_intensity, mood_emb1, mood_emb2, genre_emb1, genre_emb2, duration = row
        transpo_row = get_transpositions(cid, logger=logger)

        best_combo = {"score": 0.0, "key": key, "semitone": 0, "transposed_bpm": bpm, "pitch_shift": 0.0}

        if transpo_row:
            transpo_dict = build_transposition_dict(transpo_row)
            best_combo = find_best_transposition_combo(effective_ref_key, target_bpm, transpo_dict, logger=logger)

        if best_combo["score"] == 0:
            continue

        candidate_data = {
            "bpm": bpm,
            "beat_intensity": beat_intensity,
            "mood_emb1": mood_emb1,
            "mood_emb2": mood_emb2,
            "genre_emb1": genre_emb1,
            "genre_emb2": genre_emb2,
            "duration": duration
        }

        scores = compute_candidate_scores(
            ref_bpm, ref_duration, ref_beat_intensity,
            ref_mood_emb1, ref_mood_emb2, ref_genre_emb1, ref_genre_emb2,
            candidate_data, best_combo
        )
        total_score = compute_total_score(scores, weights)

        compatibles.append({
            "track_id": cid,
            "bpm": bpm,
            "key": best_combo["key"],
            "mood": row[4],  # mood = mood_emb1 (?)
            "beat_intensity": beat_intensity,
            "score": round(total_score, 3),
            "diagnostic": ", ".join([f"{k}_score={scores[k]:.2f}" for k in scores])
        })

    return compatibles
