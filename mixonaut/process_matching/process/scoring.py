"""
2020-08-20 module hub de scoring pour le matching.
"""

from __future__ import annotations

from mixonaut.db.matching.matching_queries import get_transpositions
from mixonaut.process_matching.models.models import (
    BestCandidate,
    CandidateTrack,
    TrackFeatures,
    TrackMatch,
    TranspoCombo,
)
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
    ref_beat_intensity: float,
    ref_mood_emb1: float,
    ref_mood_emb2: float,
    ref_genre_emb1: float,
    ref_genre_emb2: float,
    candidate: TrackFeatures,  # dict typé
    best_combo: TranspoCombo,  # alias de BestCandidate
) -> dict[str, float]:
    """
    Calcule les sous-scores normalisés ∈ [0,1] pour chaque dimension.

    Les clés retournées DOIVENT être : 'bpm', 'key', 'beat', 'mood', 'genre', 'duration'.
    """
    return {
        "key": float(best_combo["score"]),
        "bpm": float(
            calculate_bpm_similarity(ref_bpm=ref_bpm, candidate_bpm=candidate["bpm"])
        ),
        "genre": float(
            calculate_genre_sim_score(
                ref_emb1=ref_genre_emb1,
                ref_emb2=ref_genre_emb2,
                emb1=candidate["genre_emb1"],
                emb2=candidate["genre_emb2"],
            )
        ),
        "duration": float(
            calculate_duration_similarity(
                ref_duration=ref_duration, candidate_duration=candidate["duration"]
            )
        ),
        "beat": float(
            calculate_beat_intensity_score(
                candidate["beat_intensity"], ref_beat_intensity
            )
        ),
        "mood": float(
            calculate_mood_sim_score(
                ref_emb1=ref_mood_emb1,
                ref_emb2=ref_mood_emb2,
                emb1=candidate["mood_emb1"],
                emb2=candidate["mood_emb2"],
            )
        ),
    }


# def compute_total_score(scores: dict[str, Any], weights: dict[str, int]) -> float:
#     """
#     Compute the total score by multiplying each score with its corresponding weight and summing them up.

#     Args:
#         scores (dict): A dictionary containing the scores for different parameters.
#         weights (dict): A dictionary containing the weights for different parameters.

#     Returns:
#         float: The total score.
#     """
#     return sum(scores[k] * weights[k] for k in scores if k in weights)


def compute_total_score(
    scores: dict[str, float],
    weights: dict[str, float],
) -> float:
    """
    Calcule la somme pondérée.

    Les clés attendues: 'bpm','key','beat','mood','genre','duration'. Les clés manquantes sont traitées comme 0.
    """
    total = 0.0
    for k, w in weights.items():
        total += w * scores.get(k, 0.0)
    return float(total)


@with_child_logger
def get_compatible_candidates(
    candidates: list[CandidateTrack],
    ref_bpm: float,
    ref_duration: float,
    ref_beat_intensity: float,
    ref_mood_emb1: float,
    ref_mood_emb2: float,
    ref_genre_emb1: float,
    ref_genre_emb2: float,
    effective_ref_key: str,
    target_bpm: float,
    weights_type: str,
    logger: LoggerProtocol | None = None,
) -> list[TrackMatch]:
    """
    Calcule les scores de compatibilité pour chaque candidat vs.

    la référence. Retourne une liste triable de TrackMatch.
    """
    logger = ensure_logger(logger, __name__)
    weights = get_weights(weights_type)  # dict[str, float] attendu
    compatibles: list[TrackMatch] = []

    for cand in candidates:
        try:
            cid = cand["id"]
            bpm = cand["bpm"]
            key = cand["key"]

            # 1) Transposition : récupérer la ligne de transpo (si disponible)
            transpo_row = get_transpositions(cid, logger=logger)
            if transpo_row:
                transpo_dict = build_transposition_dict(
                    transpo_row
                )  # dict[str, str | float]
                best_combo: TranspoCombo = find_best_transposition_combo(
                    ref_key=effective_ref_key,
                    target_bpm=target_bpm,
                    transpo_dict=transpo_dict,
                    logger=logger,
                )
            else:
                best_combo = BestCandidate(
                    score=0.0,
                    key=key,
                    semitone=0,
                    transposed_bpm=bpm,
                    pitch_shift=0.0,
                )

                # Si la transpo n’apporte rien d’utilisable, on passe
            if best_combo["score"] <= 0.0 or best_combo["key"] is None:
                continue

            # 2) Features du candidat pour le scoring global (avec key retenue)
            candidate_data: TrackFeatures = {
                "bpm": bpm,
                "key": best_combo["key"],  # key transposée retenue
                "beat_intensity": cand["beat_intensity"],
                "mood_emb1": cand["mood_emb1"],
                "mood_emb2": cand["mood_emb2"],
                "genre_emb1": cand["genre_emb1"],
                "genre_emb2": cand["genre_emb2"],
                "duration": cand["duration"],
            }

            # 3) Scores partiels
            scores = compute_candidate_scores(
                ref_bpm=ref_bpm,
                ref_duration=ref_duration,
                ref_beat_intensity=ref_beat_intensity,
                ref_mood_emb1=ref_mood_emb1,
                ref_mood_emb2=ref_mood_emb2,
                ref_genre_emb1=ref_genre_emb1,
                ref_genre_emb2=ref_genre_emb2,
                candidate=candidate_data,
                best_combo=best_combo,  # <- OK grâce à l’alias
            )

            total_score = compute_total_score(scores, weights)  # <- plus d’erreur mypy

            # 4) Diagnostic + construction du match
            reason = ", ".join(f"{k}_score={v:.2f}" for k, v in scores.items())

            compatibles.append(
                {
                    "id": cid,
                    "score": float(round(total_score, 3)),
                    "key": candidate_data["key"],  # la key transposée choisie
                    "reason": reason,
                    "features": {
                        "id": cid,
                        "bpm": bpm,
                        "key": key,  # key originale du candidat (utile debug/export)
                        "beat_intensity": cand["beat_intensity"],
                        "mood_emb1": cand["mood_emb1"],
                        "mood_emb2": cand["mood_emb2"],
                        "genre_emb1": cand["genre_emb1"],
                        "genre_emb2": cand["genre_emb2"],
                        "duration": cand["duration"],
                    },
                }
            )

        except KeyError as exc:  # pylint: disable=broad-except
            logger.error(
                "Clé manquante pour le candidat %s: %s", cand.get("id", "?"), exc
            )
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception(
                "Erreur pendant l'évaluation du candidat %s: %s",
                cand.get("id", "?"),
                exc,
            )

    return compatibles
