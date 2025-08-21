"""
2020-08-20 module de paramétrage pour le matching.
"""


def get_weights(profile: str = "standard") -> dict[str, int]:
    """
    Renvoie les poids associés à un profil de personnalisation.

    Args:
        profile (str): Le nom du profil. Si null ou vide, utilise 'standard'.

    Returns:
        dict[str, float]: Les poids associés au profil.
    """
    profiles = {
        "standard": {
            "key": 10,
            "genre_sim": 30,
            "beat_intensity": 15,
            "bpm_sim": 10,
            "mood_sim": 30,
            "duration_sim": 5,
        },
        "alternatif": {
            "key": 30,
            "genre_sim": 10,
            "beat_intensity": 25,
            "bpm_sim": 10,
            "mood_sim": 15,
            "duration_sim": 10,
        },
        # Ajoute d’autres profils ici
    }
    return profiles.get(profile, profiles["standard"])
