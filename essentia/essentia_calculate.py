from typing import Optional, Dict
from utils.config import GENRE_FIELDS, CAMELOT_MAP, ENHARMONIC_MAP
from pathlib import Path
from utils.logger import get_logger
logname = __name__.split(".")[-1]


def calculate_beat_intensity(features: dict, logname=logname) -> float:
    """
    Calcule une valeur d'intensité du beat sur une échelle de 0 à 10,
    en combinant plusieurs caractéristiques musicales issues d'Essentia.

    Args:
        features (dict): dictionnaire des attributs musicaux extraits (via parser JSON)

    Returns:
        float: score d'intensité du beat
    """
    logger = get_logger(logname)
    try:
        bpm = features.get("bpm_essentia") or 0
        average_loudness = features.get("average_loudness") or 0
        beats_count = features.get("beats_count") or 0
        beats_loudness_mean = features.get("beats_loudness_mean") or 0
        danceability = features.get("danceability") or 0

        # Normalisation + pondération (adaptable selon préférences)
        score = (
            (bpm / 200) * 0.3 +
            (average_loudness / 60) * 0.2 +
            (beats_count / 1000) * 0.2 +
            (beats_loudness_mean / 1.0) * 0.2 +
            (danceability) * 0.1
        ) * 10

        return round(min(score, 10.0), 2)

    except Exception as e:
        logger.warning(f"Erreur calcul beat_intensity : {e}")
        return 0.0


def compute_energy_level(features: dict, logname=logname) -> float | None:
    """
    Calcule un niveau d'énergie global à partir de caractéristiques audio issues d'Essentia.

    :param features: dictionnaire contenant les features extraites
    :return: float normalisé [0.0 - 1.0] ou None en cas d'erreur
    """
    logger = get_logger(logname)
    try:
        def norm(val, max_val):
            return min(val / max_val, 1.0)

        centroid = norm(features.get("spectral_centroid", 0), 5000.0)
        flux = norm(features.get("spectral_flux", 0), 0.4)
        complexity = norm(features.get("spectral_complexity", 0), 30.0)
        energy = norm(features.get("spectral_energy", 0), 0.3)
        loudness = norm(features.get("average_loudness", 0), 1.5)
        zcr = norm(features.get("zerocrossingrate", 0), 0.2)
        beats_loudness = norm(features.get("beats_loudness", 0), 0.3)
        bpm = norm(features.get("bpm_essentia", 0), 180.0)
        dyn_complex = norm(features.get("dynamic_complexity", 0), 10.0)

        energy_level = round(
            0.15 * loudness +
            0.15 * centroid +
            0.1 * flux +
            0.1 * energy +
            0.1 * beats_loudness +
            0.1 * bpm +
            0.1 * complexity +
            0.1 * dyn_complex +
            0.1 * zcr,
            3
        )
        return energy_level

    except Exception as e:
        logger.warning(f"[ERROR] Échec calcul energy_level: {e}")
        raise
