"""
2020-08-20 module de paramétrage pour le matching.
"""


def get_weights(profile: str = "standard") -> dict[str, float]:
    """
    Poids par profil, clés alignées avec compute_candidate_scores:

    'bpm', 'key', 'beat', 'mood', 'genre', 'duration'. Retourne des floats normalisées (somme = 1.0).
    """
    profiles: dict[str, dict[str, int]] = {
        "standard": {
            "key": 10,
            "genre": 30,
            "beat": 15,
            "bpm": 10,
            "mood": 30,
            "duration": 5,
        },
        "alternatif": {
            "key": 30,
            "genre": 10,
            "beat": 25,
            "bpm": 10,
            "mood": 15,
            "duration": 10,
        },
    }
    raw = profiles.get(profile, profiles["standard"])
    total = float(sum(raw.values())) or 1.0
    return {k: v / total for k, v in raw.items()}
