"""
2020-08-20 module de paramétrage pour le matching.
"""

WEIGHT_PROFILES: dict[str, dict[str, int]] = {
    "standard": {
        "key": 5,
        "genre": 50,
        "beat": 20,
        "bpm": 10,
        "mood": 10,
        "duration": 5,
    },
    "sim": {
        "key": 0,
        "genre": 80,
        "beat": 20,
        "bpm": 0,
        "mood": 0,
        "duration": 0,
    },
}


def get_weights(profile: str = "standard") -> dict[str, float]:
    """
    Poids par profil, clés alignées avec compute_candidate_scores:

    'bpm', 'key', 'beat', 'mood', 'genre', 'duration'.

    Retourne des floats normalisées (somme = 1.0).
    """
    raw = WEIGHT_PROFILES.get(
        profile,
        WEIGHT_PROFILES["standard"],
    )

    total = float(sum(raw.values())) or 1.0

    return {key: value / total for key, value in raw.items()}
