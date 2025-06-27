from datetime import datetime
from utils.config import EXPORT_COMPATIBLE_TRACKS
from db.matching_queries import get_track_features, get_transpositions, get_candidate_tracks
from matching.key_process import build_transposition_dict, find_best_transposition_combo
from matching.scoring import compute_candidate_scores, compute_total_score
from matching.export_markdown import group_matches_by_transition_type
from utils.logger import get_logger
import math

logname = __name__.split(".")[-1]
logger = get_logger(logname)

WEIGHTS = {
                "key": 10,
                "genre_sim": 30,
                "beat_intensity": 15,
                "bpm_sim": 10,
                "mood": 5,
                "mood_sim": 25,
                "duration_sim": 5
            }

def find_compatible_tracks(
    track_id: int,
    target_bpm: float = None,
    tolerance_bpm_percent: float = 8.0,
    tolerance_energy: int = 20,
    key_match: bool = True,
    mood_match: bool = True,
    max_results: int = 10,
    grouped: bool = False,
    logname: str = logname
) -> list[dict] | dict[str, list[dict]]:
    try:
        ref = get_track_features(track_id, logname)
        if not ref:
            logger.warning(f"Track ID {track_id} introuvable dans audio_features")
            return []

        ref_bpm, ref_key, ref_mood, ref_beat_intensity, ref_mood_emb1, ref_mood_emb2, ref_genre_emb1, ref_genre_emb2, ref_duration = ref
        effective_ref_key = ref_key

        if target_bpm is None:
            target_bpm = ref_bpm
        else:
            ref_pitch_shift = 12 * math.log2(target_bpm / ref_bpm)
            ref_semitone_shift = round(ref_pitch_shift)
            ref_transpo = get_transpositions(track_id, logname)
            if ref_transpo:
                transpo_dict = build_transposition_dict(ref_transpo)
                key_col = f"key_{'plus' if ref_semitone_shift > 0 else 'minus' if ref_semitone_shift < 0 else '0'}_{abs(ref_semitone_shift)}"
                if key_col in transpo_dict and transpo_dict[key_col]:
                    effective_ref_key = transpo_dict[key_col]

        bpm_min = target_bpm * (1 - tolerance_bpm_percent / 100)
        bpm_max = target_bpm * (1 + tolerance_bpm_percent / 100)
        candidates = get_candidate_tracks(track_id, logname)

        compatibles = []
        for row in candidates:
            cid, bpm, key, mood, beat_intensity, mood_emb1, mood_emb2, genre_emb1, genre_emb2, duration = row
            transpo_row = get_transpositions(cid, logname)

            best_combo = {"score": 0.0, "key": key, "semitone": 0, "transposed_bpm": bpm, "pitch_shift": 0.0}

            if transpo_row:
                transpo_dict = build_transposition_dict(transpo_row)
                best_combo = find_best_transposition_combo(effective_ref_key, bpm, bpm_min, bpm_max, transpo_dict)
            elif not key_match:
                best_combo["score"] = 0.1

            if best_combo["score"] == 0:
                continue

            candidate_data = {
                "bpm": bpm,
                "mood": mood,
                "beat_intensity": beat_intensity,
                "mood_emb1": mood_emb1,
                "mood_emb2": mood_emb2,
                "genre_emb1": genre_emb1,
                "genre_emb2": genre_emb2,
                "duration": duration
            }

            scores = compute_candidate_scores(
                ref_bpm, ref_duration, ref_beat_intensity, ref_mood,
                ref_mood_emb1, ref_mood_emb2, ref_genre_emb1, ref_genre_emb2,
                candidate_data, best_combo,
                tolerance_energy, mood_match
            )
            total_score = compute_total_score(scores, WEIGHTS)

            compatibles.append({
                "track_id": cid,
                "bpm": bpm,
                "key": best_combo["key"],
                "mood": mood,
                "beat_intensity": beat_intensity,
                "score": round(total_score, 3),
                "diagnostic": ", ".join([f"{k}_score={scores[k]:.2f}" for k in scores])
            })

        if not grouped:
            return sorted(compatibles, key=lambda x: x["score"], reverse=True)[:max_results]
        else:
            return group_matches_by_transition_type(compatibles, effective_ref_key, max_results)

    except Exception as e:
        logger.exception(f"Erreur dans find_compatible_tracks: {e}")
        return []
