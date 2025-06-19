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
        spectral_flux = features.get("spectral_flux") or 0
        dynamic_complexity = features.get("dynamic_complexity") or 0

        # Normalisation + pondération (adaptable selon préférences)
        score = (
            (beats_loudness_mean or 0) * 4 +         # puissance moyenne des beats
            (spectral_flux or 0) * 3 +               # variation spectrale : mouvement
            (dynamic_complexity or 0) * 2 +          # complexité dynamique
            (danceability or 0) * 1
            )

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
        spectral_flux = norm(features.get("spectral_flux", 0), 0.4)
        complexity = norm(features.get("spectral_complexity", 0), 30.0)
        spectral_energy = norm(features.get("spectral_energy", 0), 0.3)
        average_loudness = norm(features.get("average_loudness", 0), 1.5)
        zcr = norm(features.get("zerocrossingrate", 0), 0.2)
        beats_loudness_mean = norm(features.get("beats_loudness_mean", 0), 0.3)
        bpm = norm(features.get("bpm_essentia", 0), 180.0)
        dynamic_complexity = norm(features.get("dynamic_complexity", 0), 10.0)
        
        energy_level = round(
        (spectral_energy or 0) * 3 +
        (beats_loudness_mean or 0) * 3 +
        (spectral_flux or 0) * 2 +
        (average_loudness or 0) * 1 +
        (dynamic_complexity or 0) * 1,
        3
        )
        print(f"energy_level {energy_level}")
        return energy_level

    except Exception as e:
        logger.warning(f"[ERROR] Échec calcul energy_level: {e}")
        raise
