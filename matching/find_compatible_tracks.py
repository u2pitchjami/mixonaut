from datetime import datetime
from utils.config import EXPORT_COMPATIBLE_TRACKS
from db.matching_queries import get_track_features, get_candidate_tracks
from matching.key_process import get_effective_ref_key
from matching.scoring import compute_candidate_scores, compute_total_score, get_compatible_candidates
from matching.export_markdown import group_matches_by_transition_type
from utils.logger import get_logger, with_child_logger
import math

@with_child_logger 
def find_compatible_tracks(
    track_id: int,
    target_bpm: float = None,
    max_results: int = 10,
    grouped: bool = False,
    weights_type: str = "standard",
    logger: str = logger
) -> list[dict] | dict[str, list[dict]]:
    try:
        ref = get_track_features(track_id, logger=logger)
        if not ref:
            logger.warning(f"Track ID {track_id} introuvable dans audio_features")
            return []

        ref_bpm, ref_key, ref_beat_intensity, ref_mood_emb1, ref_mood_emb2, ref_genre_emb1, ref_genre_emb2, ref_duration = ref
        effective_ref_key = ref_key

        target_bpm = target_bpm or ref_bpm
        effective_ref_key = get_effective_ref_key(track_id, ref_bpm, ref_key, target_bpm, logger=logger)
        
        candidates = get_candidate_tracks(track_id, logger=logger)
        compatibles = get_compatible_candidates(
            candidates,
            ref_bpm, ref_duration, ref_beat_intensity,
            ref_mood_emb1, ref_mood_emb2, ref_genre_emb1, ref_genre_emb2,
            effective_ref_key, target_bpm,
            weights_type,
            logger=logger
        )        

        if not grouped:
            return sorted(compatibles, key=lambda x: x["score"], reverse=True)[:max_results]
        else:
            return group_matches_by_transition_type(compatibles, effective_ref_key, max_results, logger=logger)

    except Exception as e:
        logger.exception(f"Erreur dans find_compatible_tracks: {e}")
        return []
