from utils.logger import get_logger
from matching.others_process import calculate_mood_score, calculate_mood_sim_score, calculate_bpm_similarity, calculate_beat_intensity_score, calculate_duration_similarity, calculate_genre_sim_score
logname = __name__.split(".")[-1]
logger = get_logger(logname)

def compute_candidate_scores(
    ref_bpm: float,
    ref_duration: float,
    ref_beat_intensity: int,
    ref_mood: str,
    ref_mood_emb1: float,
    ref_mood_emb2: float,
    ref_genre_emb1: float,
    ref_genre_emb2: float,
    candidate: dict,
    best_combo: dict,
    tolerance_energy: int,
    mood_match: bool
) -> dict:
    return {
        "key": best_combo["score"],
        "bpm_sim": calculate_bpm_similarity(ref_bpm=ref_bpm, candidate_bpm=candidate["bpm"]),
        "genre_sim": calculate_genre_sim_score(ref_emb1=ref_genre_emb1, ref_emb2=ref_genre_emb2, emb1=candidate["genre_emb1"], emb2=candidate["genre_emb2"]),
        "duration_sim": calculate_duration_similarity(ref_duration=ref_duration, candidate_duration=candidate["duration"]),
        "beat_intensity": calculate_beat_intensity_score(candidate["beat_intensity"], ref_beat_intensity, tolerance_energy),
        "mood": calculate_mood_score(candidate["mood"], ref_mood, mood_match),
        "mood_sim": calculate_mood_sim_score(ref_emb1=ref_mood_emb1, ref_emb2=ref_mood_emb2, emb1=candidate["mood_emb1"], emb2=candidate["mood_emb2"])
    }

def compute_total_score(scores: dict, weights: dict) -> float:
    return sum(scores[k] * weights[k] for k in scores if k in weights)