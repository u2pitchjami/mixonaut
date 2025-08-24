"""
2025-08-20.

modules de calcul du beat intensity .
"""

from typing import Any

from mixonaut.utils.logger import LoggerProtocol, ensure_logger, with_child_logger


@with_child_logger
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
        spectral_flux = features.get("spectral_flux", 0.0)
        # print(f"spectral_flux : {spectral_flux * 1000 * 0.20}")
        spectral_rms_mean = features.get("spectral_rms_mean", 0.0)
        # print(f"spectral_rms_mean : {spectral_rms_mean * 10000 * 0.15}")
        average_loudness = features.get("average_loudness", 0.0)
        # print(f"average_loudness : {average_loudness * 100 * 0.10}")
        spectral_energy = features.get("spectral_energy", 0.0)
        # print(f"spectral_energy : {spectral_energy * 1000 * 0.10}")
        dynamic_complexity = features.get("dynamic_complexity", 0.0)
        # print(f"dynamic_complexity : {dynamic_complexity * 10 * 0.15}")
        onset_rate = features.get("onset_rate", 0.0)
        # print(f"onset_rat : {onset_rate * 10 * 0.15}")
        beats_loudness_mean = features.get("beats_loudness_mean", 0.0)
        # print(f"beats_loudness_mean : {beats_loudness_mean * 1000 * 0.15}")

        # Pondérations (en %)
        score = (
            spectral_flux * 0.20  # ex: 0.1 → 10 * 0.2 = 2.0
            + spectral_rms_mean * 0.15  # ex: 0.005 → 10 * 0.15 = 1.5
            + average_loudness * 0.10  # ex: 0.9 → 90 * 0.1 = 9.0
            + spectral_energy * 0.10  # ex: 0.05 → 10 * 0.1 = 1.0
            + dynamic_complexity * 0.15  # ex: 4.0 → 6 * 0.15 = 0.9
            + onset_rate * 0.15  # ex: 4.5 → 9 * 0.15 = 1.35
            + beats_loudness_mean * 0.15  # ex: 0.1 → 10 * 0.15 = 1.5
        ) * 45
        return float(round(score, 2))
    except Exception as e:
        logger.warning(f"Erreur calcul beat_intensity : {e}")
        return 0.0
