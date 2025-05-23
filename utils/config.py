# config.py
from dotenv import load_dotenv
from pathlib import Path
import os
import sys

# Chargement du .env à la racine du projet
env_path = Path(__file__).resolve().parent.parent / ".env"
print(env_path)
load_dotenv(dotenv_path=env_path, override=True)

# --- Fonctions utilitaires ---

def get_required(key: str) -> str:
    value = os.getenv(key)
    if value is None:
        print(f"[CONFIG ERROR] La variable {key} est requise mais absente.")
        sys.exit(1)
    return value

def get_bool(key: str, default: str = "false") -> bool:
    return os.getenv(key, default).lower() in ("true", "1", "yes")

def get_str(key: str, default: str = "") -> str:
    return os.getenv(key, default)

def get_int(key: str, default: int = 0) -> int:
    try:
        return int(os.getenv(key, str(default)))
    except ValueError:
        print(f"[CONFIG ERROR] La variable {key} doit être un entier.")
        sys.exit(1)

# --- Variables d'environnement accessibles globalement ---

#BEETS
BEETS_DB = get_required("BEETS_DB_PATH")
BEETS_CONFIG_DIR = get_required("BEETS_CONFIG_DIR")
BEETS_BACKUP_DIR = get_str("BEETS_BACKUP_DIR", "./sav_base")
BEETS_LOGS = get_required("BEETS_LOGS")
BEETS_MANUAL_LIST = get_str("BEETS_MANUAL_LIST", "beets_manuel.txt")
BEETS_CONFIG_MANUEL = get_required("BEETS_CONFIG_MANUEL")
BEETS_CONFIG_NORMAL = get_required("BEETS_CONFIG_NORMAL")
BEETS_CONFIG = get_required("BEETS_CONFIG")
BEETS_RECAP_DIR = get_required("BEETS_RECAP_DIR")
REPORT_PATH = get_required("REPORT_PATH")

#LOGS
LOG_FILE_PATH = get_str("LOG_FILE_PATH", "logs")
LOG_ROTATION_DAYS = get_int("LOG_ROTATION_DAYS", 100)

#ESSENTIA
PROF_ESSENTIA = get_required("PROF_ESSENTIA")
ESSENTIA_SAV_JSON = get_str("ESSENTIA_SAV_JSON", "data/tsav_json")
ESSENTIA_TEMP_AUDIO = get_str("ESSENTIA_TEMP_AUDIO", "data/temp_audio")
ESSENTIA_TEMP_JSON = get_str("ESSENTIA_TEMP_JSON", "data/temp_json")
SCRIPT_PATH_ESSENTIA = get_required("SCRIPT_PATH_ESSENTIA")

#PATHS
MUSIC_BASE_PATH = get_required("MUSIC_BASE_PATH")
HOST_MUSIC = get_required("HOST_MUSIC_PREFIX")
BEETS_MUSIC = get_required("BEETS_MUSIC_PREFIX")
WINDOWS_MUSIC = get_required("WINDOWS_MUSIC")
MANUAL_LIST = get_str("MANUAL_LIST_PATH", "import_manuel.txt")
BEETS_IMPORT_PATH = get_required("BEETS_IMPORT_PATH")
SCRIPT_DIR = get_required("SCRIPT_DIR")

#DB
MIX_DB = get_required("MIX_DB")

EDM_GENRES = {"techno", "house", "trance", "edm", "dance", "psychedelic", "rave", "space"}
AUDIO_EXTENSIONS = {'.mp3', '.flac', '.wav', '.ogg', '.m4a', '.aac', '.alac', '.wma'}
IGNORED_EXTENSIONS = {
    '.jpg', '.jpeg', '.png', '.nfo', '.txt', '.log', '.cue',
    '.pdf', '.db', '.ini', '.url', '.sfv', '.m3u'
}

CAMELOT_ORDER = [
    "1A", "2A", "3A", "4A", "5A", "6A", "7A", "8A", "9A", "10A", "11A", "12A",
    "1B", "2B", "3B", "4B", "5B", "6B", "7B", "8B", "9B", "10B", "11B", "12B"
]
SEMITONE_SHIFT_VALUES = [i * 3 for i in range(-4, 5)]  # -12 à +12

ESSENTIA_MAPPING = {
    "average_loudness": ["lowlevel", "average_loudness"],
    "chords_changes_rate": ["tonal", "chords_changes_rate"],
    "chords_key": ["tonal", "chords_key"],
    "chords_number_rate": ["tonal", "chords_number_rate"],
    "chords_scale": ["tonal", "chords_scale"],
    "danceable": ["highlevel", "danceability", "value"],
    "danceability": ["highlevel", "danceability", "probability"],
    "rhythm_danceability": ["rhythm", "danceability"],
    "gender": ["highlevel", "gender", "value"],
    "gender_probability": ["highlevel", "gender", "probability"],
    "genre_dortmund": ["highlevel", "genre_dortmund", "value"],
    "genre_dortmund_probability": ["highlevel", "genre_dortmund", "probability"],
    "genre_electronic": ["highlevel", "genre_electronic", "value"],
    "genre_electronic_probability": ["highlevel", "genre_electronic", "probability"],
    "genre_rosamerica": ["highlevel", "genre_rosamerica", "value"],
    "genre_rosamerica_probability": ["highlevel", "genre_rosamerica", "probability"],
    "genre_tzanetakis": ["highlevel", "genre_tzanetakis", "value"],
    "genre_tzanetakis_probability": ["highlevel", "genre_tzanetakis", "probability"],
    "ismir04_rhythm": ["highlevel", "ismir04_rhythm", "value"],
    "ismir04_rhythm_probability": ["highlevel", "ismir04_rhythm", "probability"],
    "mood_acoustic": ["highlevel", "mood_acoustic", "value"],
    "mood_acoustic_probability": ["highlevel", "mood_acoustic", "probability"],
    "mood_aggressive": ["highlevel", "mood_aggressive", "value"],
    "mood_aggressive_probability": ["highlevel", "mood_aggressive", "probability"],
    "mood_electronic": ["highlevel", "mood_electronic", "value"],
    "mood_electronic_probability": ["highlevel", "mood_electronic", "probability"],
    "mood_happy": ["highlevel", "mood_happy", "value"],
    "mood_happy_probability": ["highlevel", "mood_happy", "probability"],
    "mood_party": ["highlevel", "mood_party", "value"],
    "mood_party_probability": ["highlevel", "mood_party", "probability"],
    "mood_relaxed": ["highlevel", "mood_relaxed", "value"],
    "mood_relaxed_probability": ["highlevel", "mood_relaxed", "probability"],
    "mood_sad": ["highlevel", "mood_sad", "value"],
    "mood_sad_probability": ["highlevel", "mood_sad", "probability"],
    "moods_mirex": ["highlevel", "moods_mirex", "value"],
    "moods_mirex_probability": ["highlevel", "moods_mirex", "probability"],
    "beats_count": ["rhythm", "beats_count"],
    "timbre": ["highlevel", "timbre", "value"],
    "timbre_probability": ["highlevel", "timbre", "probability"],
    "tonal_atonal": ["highlevel", "tonal_atonal", "value"],
    "tonal_atonal_probability": ["highlevel", "tonal_atonal", "probability"],
    "voice_instrumental": ["highlevel", "voice_instrumental", "value"],
    "voice_instrumental_probability": ["highlevel", "voice_instrumental", "probability"],
    "bpm_essentia": ["rhythm", "bpm"],
    "beats_loudness_mean": ["rhythm", "beats_loudness", "mean"],
    "spectral_centroid": ["lowlevel", "spectral_centroid", "mean"],
    "spectral_flux": ["lowlevel", "spectral_flux", "mean"],
    "spectral_complexity": ["lowlevel", "spectral_complexity", "mean"],
    "spectral_energy": ["lowlevel", "spectral_energy", "mean"],
    "zerocrossingrate": ["lowlevel", "zerocrossingrate", "mean"],
    "dynamic_complexity": ["lowlevel", "dynamic_complexity"]
}
MOOD_KEYS = [
    "acoustic",
    "aggressive",
    "electronic",
    "happy",
    "party",
    "relaxed",
    "sad"
]
GENRE_FIELDS = [
    "genre_dortmund",
    "genre_electronic",
    "genre_rosamerica",
    "genre_tzanetakis"
]
RETRO_MIXONAUT_BEETS_test = {"mood"}
RETRO_MIXONAUT_BEETS = {"mood", "essentia_genres", "energy_level", "beat_intensity"}