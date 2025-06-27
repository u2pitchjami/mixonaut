from utils.logger import get_logger
from utils.utils_div import sanitize_value
from essentia.essentia_calculate import calculate_beat_intensity, compute_energy_level
from essentia.essentia_mood import compute_mood_vector, get_dominant_mood
from essentia.essentia_genre import get_dominant_genre
from essentia.essentia_key import get_best_key_from_essentia, convert_to_camelot
from pathlib import Path

logname = __name__.split(".")[-1]

def enrich_features(track_features, logname=logname):
    logger = get_logger(logname)
    try:
        track_features["bpm"] = sanitize_value(track_features.get("bpm"), "bpm")
        track_features["rg_track_gain"] = sanitize_value(track_features.get("rg_track_gain"), "rg_gain")

        track_features["beat_intensity"] = calculate_beat_intensity(track_features, logname=logname)
        logger.debug(f"beat_intensity : {track_features['beat_intensity']}")

        #track_features["energy_level"] = compute_energy_level(track_features, logname=logname)
        #logger.debug(f"energy_level : {track_features['energy_level']}")

        mood_vector = compute_mood_vector(track_features, logname=logname)
        logger.debug(f"mood_vector : {mood_vector}")

        track_features["mood"] = get_dominant_mood(mood_vector)
        logger.debug(f"mood : {track_features['mood']}")

        track_features["genre"] = get_dominant_genre(track_features)
        logger.debug(f"get_dominant_genre : {track_features['genre']}")

        best_key_data = get_best_key_from_essentia(track_features)
        if best_key_data:
            camelot = convert_to_camelot(best_key_data["key"], best_key_data["scale"])
            track_features["initial_key"] = sanitize_value(camelot, "key")
            logger.debug(f"initial_key : {track_features['initial_key']}")

        return track_features
    except Exception as e:
        logger.error(f"Erreur enrichissement features : {e}")
        return track_features