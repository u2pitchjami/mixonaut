"""
2025-08-20.

modules de calcul du beat intensity .
"""

from typing import Any
import math
from mixonaut.utils.logger import LoggerProtocol, ensure_logger


def calculate_beat_intensity(
    features: dict[str, Any], logger: LoggerProtocol | None = None
) -> float:
    """
    Calcule une valeur d'intensité du beat sur une échelle de 0 à 10, en combinant plusieurs caractéristiques musicales
    issues d'Essentia.

    Args:
        features (dict): dictionnaire des attributs musicaux extraits (via parser JSON)

    Returns:
        float: score d'intensité du beat
    """
    logger = ensure_logger(logger, __name__)
    try:
        dynamic_complexity = float(features.get("dynamic_complexity") or 0.0)
        dynamic_complexity_score = math.log1p(dynamic_complexity) or 0.0
        spectral_flux = float(features.get("spectral_flux") or 0.0)
        spectral_rms_mean = float(features.get("spectral_rms_mean") or 0.0)
        average_loudness = float(features.get("average_loudness") or 0.0)
        spectral_energy = float(features.get("spectral_energy") or 0.0)
        onset_rate = float(features.get("onset_rate") or 0.0)
        beats_loudness_mean = float(features.get("beats_loudness_mean") or 0.0)

        # Pondérations (en %)
        score = (
            spectral_flux * 0.20  # ex: 0.1 → 10 * 0.2 = 2.0
            + spectral_rms_mean * 0.15  # ex: 0.005 → 10 * 0.15 = 1.5
            + average_loudness * 0.10  # ex: 0.9 → 90 * 0.1 = 9.0
            + spectral_energy * 0.10  # ex: 0.05 → 10 * 0.1 = 1.0
            + dynamic_complexity_score * 0.15  # ex: 4.0 → 6 * 0.15 = 0.9
            + onset_rate * 0.15  # ex: 4.5 → 9 * 0.15 = 1.35
            + beats_loudness_mean * 0.15  # ex: 0.1 → 10 * 0.15 = 1.5
        ) * 45
        return float(round(score, 2))
    except Exception as e:
        logger.warning(f"Erreur calcul beat_intensity : {e}")
        return 0.0
