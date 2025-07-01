from utils.config import GENRE_FIELDS, CAMELOT_MAP, ENHARMONIC_MAP
from pathlib import Path
from utils.logger import get_logger, with_child_logger

@with_child_logger
def calculate_beat_intensity(features: dict, logger=None) -> float:
    """
    Calcule une valeur d'intensité du beat sur une échelle de 0 à 10,
    en combinant plusieurs caractéristiques musicales issues d'Essentia.

    Args:
        features (dict): dictionnaire des attributs musicaux extraits (via parser JSON)

    Returns:
        float: score d'intensité du beat
    """
    try:        
        spectral_flux = features.get("spectral_flux", 0.0)
        #print(f"spectral_flux : {spectral_flux * 1000 * 0.20}")
        spectral_rms_mean = features.get("spectral_rms_mean", 0.0)
        #print(f"spectral_rms_mean : {spectral_rms_mean * 10000 * 0.15}")
        average_loudness = features.get("average_loudness", 0.0)
        #print(f"average_loudness : {average_loudness * 100 * 0.10}")
        spectral_energy = features.get("spectral_energy", 0.0)
        #print(f"spectral_energy : {spectral_energy * 1000 * 0.10}")
        dynamic_complexity = features.get("dynamic_complexity", 0.0)
        #print(f"dynamic_complexity : {dynamic_complexity * 10 * 0.15}")
        onset_rate = features.get("onset_rate", 0.0)
        #print(f"onset_rat : {onset_rate * 10 * 0.15}")
        beats_loudness_mean = features.get("beats_loudness_mean", 0.0)
        #print(f"beats_loudness_mean : {beats_loudness_mean * 1000 * 0.15}")        

        # Pondérations (en %)
        score = (
            spectral_flux * 0.20 +           # ex: 0.1 → 10 * 0.2 = 2.0
            spectral_rms_mean * 0.15 +      # ex: 0.005 → 10 * 0.15 = 1.5
            average_loudness * 0.10 +        # ex: 0.9 → 90 * 0.1 = 9.0
            spectral_energy * 0.10 +         # ex: 0.05 → 10 * 0.1 = 1.0
            dynamic_complexity * 0.15 +       # ex: 4.0 → 6 * 0.15 = 0.9
            onset_rate * 0.15 +                # ex: 4.5 → 9 * 0.15 = 1.35
            beats_loudness_mean  * 0.15       # ex: 0.1 → 10 * 0.15 = 1.5
        ) * 45
        return round(score, 2)
    except Exception as e:
        logger.warning(f"Erreur calcul beat_intensity : {e}")
        return 0.0

@with_child_logger
def compute_energy_level(features: dict, logger=None) -> float | None:
    """
    Calcule un niveau d'énergie global à partir de caractéristiques audio issues d'Essentia.

    :param features: dictionnaire contenant les features extraites
    :return: float normalisé [0.0 - 1.0] ou None en cas d'erreur
    """
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
