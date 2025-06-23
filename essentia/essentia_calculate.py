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
        def norm(val, max_val):
            return min(val / max_val, 1.0)
        
        beats_loudness_mean = norm(features.get("beats_loudness_mean", 0), 0.4)
        onset_rate = norm(features.get("onset_rate", 0), 10)
        spectral_flux = norm(features.get("spectral_flux", 0), 0.3)
        zcr = norm(features.get("zerocrossingrate", 0), 0.2)
        dynamic_complexity = norm(features.get("dynamic_complexity", 0), 60.0)
        average_loudness = norm(features.get("average_loudness", 0), 1.0)
        beats_count = norm(features.get("beats_count", 0), 1000.0)
        danceability = norm(features.get("danceability", 0), 1.0)
                
        score = round(
            (beats_loudness_mean or 0) * 3.5 +         # puissance moyenne des beats
            (onset_rate or 0) * 2.5 +
            (spectral_flux or 0) * 1.5 +
            (zcr or 0) * 1 +
            (dynamic_complexity or 0) * 0.8 +
            (average_loudness or 0) * 0.4 +
            (beats_count or 0) * 0.2 +
            (danceability or 0) * 0.1,
            3
            )
        #print(f"score {score} ")
        #print(f"beats_loudness_mean {beats_loudness_mean *10 * 4}, spectral_flux {spectral_flux * 3},dynamic_complexity {dynamic_complexity / 10 * 2},danceabilityn {danceability},")
        return round(min(score, 10.0), 3)

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

        spectral_centroid = norm(features.get("spectral_centroid", 0), 5000.0)
        spectral_flux = norm(features.get("spectral_flux", 0), 0.3)
        spectral_complexity = norm(features.get("spectral_complexity", 0), 30.0)
        spectral_energy = norm(features.get("spectral_energy", 0), 0.3)
        average_loudness = norm(features.get("average_loudness", 0), 1.0)
        zrc = norm(features.get("zerocrossingrate", 0), 0.2)
        beats_loudness_mean = norm(features.get("beats_loudness_mean", 0), 0.4)
        dynamic_complexity = norm(features.get("dynamic_complexity", 0), 60.0)
        
        energy_level = round(
        (beats_loudness_mean or 0) * 3 +
        (average_loudness or 0) * 2 +
        (spectral_centroid or 0) * 1 +
        (spectral_energy or 0) * 1 +
        (spectral_flux or 0) * 1 +
        (spectral_complexity or 0) * 0.5 +
        (dynamic_complexity or 0) * 0.3 +
        (zrc or 0) * 0.2,
        3
        )
        #print(f"energy_level {energy_level}")
        #print(f"spectral_energy {spectral_energy * 3}, average_loudness {average_loudness * 1}, spectral_flux {spectral_flux * 2}, dynamic_complexity {dynamic_complexity}, beats_loudness_mean {beats_loudness_mean * 3},")
        
        return energy_level

    except Exception as e:
        logger.warning(f"[ERROR] Échec calcul energy_level: {e}")
        raise
