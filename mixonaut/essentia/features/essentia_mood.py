"""
2025-08-20.

modules de traitement du mood.
"""

from typing import Any

from mixonaut.utils.config import MOOD_KEYS
from mixonaut.utils.logger import LoggerProtocol, ensure_logger, with_child_logger


@with_child_logger
def compute_mood_vector(
    features: dict[str, Any], logger: LoggerProtocol | None = None
) -> dict[str, float]:
    """
    Extrait un vecteur de mood à partir des features audio (probas Essentia).

    :param features: Dictionnaire contenant les features Essentia ou lignes DB formatées
    :param logger: Nom du logger
    :return: Dictionnaire {mood: proba} ou None si échec
    """
    logger = ensure_logger(logger, __name__)
    try:
        vector = {}
        for mood in MOOD_KEYS:
            proba_key = f"mood_{mood}_probability"
            value = features.get(proba_key)
            if value is not None:
                vector[mood] = round(float(value), 3)
            else:
                logger.debug(f"Proba non trouvée pour mood: {mood}")
                vector[mood] = 0.0

        return vector

    except Exception as e:
        logger.warning(f"[ERROR] Échec extraction mood_vector: {e}")
        raise


def get_dominant_mood(mood_vector: dict[str, float]) -> str | None:
    """
    Extrait le mood dominant à partir d'un mood_vector.

    :param mood_vector: Dictionnaire {mood: proba}
    :return: Mood dominant (str) ou None
    """
    if not mood_vector:
        return None
    # Utilise __getitem__ plutôt que .get pour que mypy comprenne bien : str -> float
    return max(mood_vector, key=mood_vector.__getitem__)
