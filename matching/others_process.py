import math

def calculate_mood_score(mood: str, ref_mood: str, mood_match=True) -> float:
    if mood_match and mood == ref_mood:
        return 1.0
    elif not mood_match:
        return 0.5
    return 0.0

def calculate_mood_sim_score(ref_emb1, ref_emb2, emb1, emb2) -> float:
    """
    Calcule un score de similarité entre deux embeddings mood 2D.
    """
    if ref_emb1 is not None and emb1 is not None:
        return max(0.0, 1 - math.sqrt((ref_emb1 - emb1)**2 + (ref_emb2 - emb2)**2))
    return 0.0

def calculate_duration_similarity(ref_duration: float, candidate_duration: float, tolerance_pct: float = 0.2) -> float:
    """
    Calcule un score de similarité basé sur la différence de durée.
    Le score est de 1.0 si la différence est nulle, et décroît linéairement jusqu'à 0 selon la tolérance (en pourcentage).

    Args:
        ref_duration (float): durée en secondes de la track de référence.
        candidate_duration (float): durée en secondes de la track candidate.
        tolerance_pct (float): tolérance maximale en pourcentage (ex: 0.1 pour 10%)

    Returns:
        float: score de similarité entre 0.0 et 1.0
    """
    if ref_duration is None or candidate_duration is None or ref_duration == 0:
        return 0.0
    tolerance = ref_duration * tolerance_pct
    diff = abs(ref_duration - candidate_duration)
    return max(0.0, 1.0 - diff / tolerance)

def calculate_energy_score(energy: int, ref_energy: int, tolerance: int) -> float:
    return max(0.0, 1 - abs(energy - ref_energy) / tolerance)

def calculate_beat_intensity_score(beat_intensity: int, ref_beat_intensity: int) -> float:
    return max(0.0, 1 - abs(beat_intensity - ref_beat_intensity) / 100)

def calculate_genre_sim_score(ref_emb1, ref_emb2, emb1, emb2) -> float:
    """
    Calcule un score de similarité entre deux embeddings genre 2D.
    """
    if ref_emb1 is not None and emb1 is not None:
        return max(0.0, 1 - math.sqrt((ref_emb1 - emb1)**2 + (ref_emb2 - emb2)**2))
    return 0.0

def cosine_similarity(vec1: list, vec2: list) -> float:
    """
    Similarité cosinus entre deux vecteurs complets (utilisable pour genre ou mood).
    """
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = math.sqrt(sum(a * a for a in vec1))
    norm2 = math.sqrt(sum(b * b for b in vec2))
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot_product / (norm1 * norm2)

def calculate_bpm_similarity(ref_bpm: float, candidate_bpm: float, tolerance_pct: float = 0.08) -> float:
    """
    Calcule un score de similarité basé sur la différence de BPM.
    Le score est de 1.0 si la différence est nulle, et décroît linéairement jusqu'à 0 selon la tolérance (en pourcentage).

    Args:
        ref_bpm (float): BPM de la track de référence.
        candidate_bpm (float): BPM de la track candidate.
        tolerance_pct (float): tolérance maximale en pourcentage (ex: 0.05 pour 5%)

    Returns:
        float: score de similarité entre 0.0 et 1.0
    """
    if ref_bpm is None or candidate_bpm is None or ref_bpm == 0:
        return 0.0
    tolerance = ref_bpm * tolerance_pct
    diff = abs(ref_bpm - candidate_bpm)
    return max(0.0, 1.0 - diff / tolerance)