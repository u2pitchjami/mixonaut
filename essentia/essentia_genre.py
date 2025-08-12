from utils.config import ELECTRO_OVERRIDE_GENRES, GENRE_PROB_DORTMUND, GENRE_PROB_ROSAMERICA, GENRE_PROB_THRESHOLD, GENRE_CANONICAL
from collections import defaultdict


def get_dominant_genre(track_features: dict) -> str:
    """
    Détermine le genre dominant à partir des outputs Essentia
    """
    # Vérifie override électro (si les deux modèles pointent vers electro/dan)
    dortmund = track_features.get("genre_dortmund")
    dortmund_p = track_features.get("genre_dortmund_probability", 0.0)    
    rosamerica = track_features.get("genre_rosamerica")
    rosamerica_p = track_features.get("genre_rosamerica_probability", 0.0)    

    if (
        dortmund in ELECTRO_OVERRIDE_GENRES
        and rosamerica in ELECTRO_OVERRIDE_GENRES
        and dortmund_p >= GENRE_PROB_DORTMUND
        and rosamerica_p >= GENRE_PROB_ROSAMERICA
    ):
        # On prend uniquement le genre_electronic
        electronic = track_features.get("genre_electronic")
        electronic_p = track_features.get("genre_electronic_probability", 0.0)
        
        return GENRE_CANONICAL.get(electronic.lower(), electronic)
    
    # Sinon, vote pondéré entre les 3 modèles généraux
    votes = defaultdict(float)
    for model in ["genre_dortmund", "genre_rosamerica", "genre_tzanetakis"]:
        genre = track_features.get(model)
        prob = track_features.get(f"{model}_probability", 0.0)
        if genre and prob >= GENRE_PROB_THRESHOLD:
            votes[genre.lower()] += prob

    if not votes:
        return None

    top_genre = max(votes.items(), key=lambda x: x[1])[0]
    return GENRE_CANONICAL.get(top_genre, top_genre)
