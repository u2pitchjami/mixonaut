# config.py
from dotenv import load_dotenv
from pathlib import Path
import os
import sys

# Chargement du .env à la racine du projet
env_path = Path(__file__).resolve().parent.parent / ".env"
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
SCRIPT_PATH_REPLAYGAIN = get_required("SCRIPT_PATH_ESSENTIA")

#PATHS
MUSIC_BASE_PATH = get_required("MUSIC_BASE_PATH")
HOST_MUSIC = get_required("HOST_MUSIC_PREFIX")
BEETS_MUSIC = get_required("BEETS_MUSIC_PREFIX")
WINDOWS_MUSIC = get_required("WINDOWS_MUSIC")
MANUAL_LIST = get_str("MANUAL_LIST_PATH", "import_manuel.txt")
BEETS_IMPORT_PATH = get_required("BEETS_IMPORT_PATH")
SCRIPT_DIR = get_required("SCRIPT_DIR")
LOCK_FILE = get_str("LOCK_FILE", "beets_db.lock")
EXPORT_COMPATIBLE_TRACKS = get_str("EXPORT_COMPATIBLE_TRACKS", "./exports")

#DB
MIX_DB = get_required("MIX_DB")
QUERIES_DIR = get_str("QUERIES_DIR", "./dashboard")

#IMAGES
IMAGE_BEETS = get_required("IMAGE_BEETS")
IMAGE_ESSENTIA = get_required("IMAGE_ESSENTIA")


EDM_GENRES = {"techno", "house", "trance", "edm", "dance", "psychedelic", "rave", "space"}
AUDIO_EXTENSIONS = {'.mp3', '.flac', '.wav', '.ogg', '.m4a', '.aac', '.alac', '.wma'}
IGNORED_EXTENSIONS = {
    '.jpg', '.jpeg', '.png', '.nfo', '.txt', '.log', '.cue',
    '.pdf', '.db', '.ini', '.url', '.sfv', '.m3u'
}

CAMELOT_ORDER = [
    "1a", "2a", "3a", "4a", "5a", "6a", "7a", "8a", "9a", "10a", "11a", "12a",
    "1b", "2b", "3b", "4b", "5b", "6b", "7b", "8b", "9b", "10b", "11b", "12b"
]
SEMITONE_SHIFT_VALUES = list(range(-12, 13))

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
    "genre_dortmund_alternative": ["highlevel", "genre_dortmund", "all", "alternative"],
    "genre_dortmund_blues": ["highlevel", "genre_dortmund", "all", "blues"],
    "genre_dortmund_electronic": ["highlevel", "genre_dortmund", "all", "electronic"],
    "genre_dortmund_folkcountry": ["highlevel", "genre_dortmund", "all", "folkcountry"],
    "genre_dortmund_funksoulrnb": ["highlevel", "genre_dortmund", "all", "funksoulrnb"],    
    "genre_dortmund_jazz": ["highlevel", "genre_dortmund", "all", "jazz"],
    "genre_dortmund_pop": ["highlevel", "genre_dortmund", "all", "pop"],
    "genre_dortmund_raphiphop": ["highlevel", "genre_dortmund", "all", "raphiphop"],
    "genre_dortmund_rock": ["highlevel", "genre_dortmund", "all", "rock"],
    "genre_electronic": ["highlevel", "genre_electronic", "value"],
    "genre_electronic_probability": ["highlevel", "genre_electronic", "probability"],
    "genre_electronic_ambient": ["highlevel", "genre_electronic", "all", "ambient"],
    "genre_electronic_dnb": ["highlevel", "genre_electronic", "all", "dnb"],
    "genre_electronic_house": ["highlevel", "genre_electronic", "all", "house"],
    "genre_electronic_techno": ["highlevel", "genre_electronic", "all", "techno"],
    "genre_electronic_trance": ["highlevel", "genre_electronic", "all", "trance"],
    "genre_rosamerica": ["highlevel", "genre_rosamerica", "value"],
    "genre_rosamerica_probability": ["highlevel", "genre_rosamerica", "probability"],
    "genre_rosamerica_cla": ["highlevel", "genre_rosamerica", "all", "cla"],
    "genre_rosamerica_dan": ["highlevel", "genre_rosamerica", "all", "dan"],
    "genre_rosamerica_hip": ["highlevel", "genre_rosamerica", "all", "hip"],
    "genre_rosamerica_jaz": ["highlevel", "genre_rosamerica", "all", "jaz"],
    "genre_rosamerica_pop": ["highlevel", "genre_rosamerica", "all", "pop"],
    "genre_rosamerica_roc": ["highlevel", "genre_rosamerica", "all", "roc"],
    "genre_rosamerica_rhy": ["highlevel", "genre_rosamerica", "all", "rhy"],
    "genre_rosamerica_spe": ["highlevel", "genre_rosamerica", "all", "spe"],
    "genre_tzanetakis": ["highlevel", "genre_tzanetakis", "value"],
    "genre_tzanetakis_probability": ["highlevel", "genre_tzanetakis", "probability"],
    "genre_tzanetakis_blu": ["highlevel", "genre_tzanetakis", "all", "blu"],
    "genre_tzanetakis_cla": ["highlevel", "genre_tzanetakis", "all", "cla"],
    "genre_tzanetakis_cou": ["highlevel", "genre_tzanetakis", "all", "cou"],
    "genre_tzanetakis_dis": ["highlevel", "genre_tzanetakis", "all", "dis"],
    "genre_tzanetakis_hip": ["highlevel", "genre_tzanetakis", "all", "hip"],
    "genre_tzanetakis_jaz": ["highlevel", "genre_tzanetakis", "all", "jaz"],
    "genre_tzanetakis_met": ["highlevel", "genre_tzanetakis", "all", "met"],
    "genre_tzanetakis_pop": ["highlevel", "genre_tzanetakis", "all", "pop"],
    "genre_tzanetakis_reg": ["highlevel", "genre_tzanetakis", "all", "reg"],
    "genre_tzanetakis_roc": ["highlevel", "genre_tzanetakis", "all", "roc"],
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
    "bpm": ["rhythm", "bpm"],
    "beats_loudness_mean": ["rhythm", "beats_loudness", "mean"],
    "onset_rate": ["rhythm", "onset_rate"],
    "spectral_centroid": ["lowlevel", "spectral_centroid", "mean"],
    "spectral_flux": ["lowlevel", "spectral_flux", "mean"],
    "spectral_complexity": ["lowlevel", "spectral_complexity", "mean"],
    "spectral_energy": ["lowlevel", "spectral_energy", "mean"],
    "spectral_rms_mean": ["lowlevel", "spectral_rms", "mean"],
    "spectral_rms_stdev": ["lowlevel", "spectral_rms", "stdev"],    
    "zerocrossingrate": ["lowlevel", "zerocrossingrate", "mean"],
    "dynamic_complexity": ["lowlevel", "dynamic_complexity"],
    "key_edma": ["tonal", "key_edma", "key"], 
    "scale_edma": ["tonal", "key_edma", "scale"],
    "strength_edma": ["tonal", "key_edma", "strength"],
    "key_krumhansl": ["tonal", "key_krumhansl", "key"], 
    "scale_krumhansl": ["tonal", "key_krumhansl", "scale"],
    "strength_krumhansl": ["tonal", "key_krumhansl", "strength"],
    "key_temperley": ["tonal", "key_temperley", "key"], 
    "scale_temperley": ["tonal", "key_temperley", "scale"],
    "strength_temperley": ["tonal", "key_temperley", "strength"],
    "rg_track_gain": ["lowlevel", "replaygain"]
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

RETRO_MIXONAUT_BEETS = {
    "mood",
    "energy_level",
    "beat_intensity",
    "bpm",
    "rg_track_gain",
    "initial_key",
    "genre"
}

CAMELOT_MAP = {
        "C":  "8B", "C#": "3B", "D":  "10B", "D#": "5B", "E":  "12B", "F":  "7B",
        "F#": "2B", "G":  "9B", "G#": "4B", "A":  "11B", "A#": "6B", "B":  "1B",
        "Cm": "5A", "C#m":"12A", "Dm": "7A", "D#m":"2A", "Em": "9A", "Fm": "4A",
        "F#m":"11A", "Gm": "6A", "G#m":"1A", "Am": "8A", "A#m":"3A", "Bm": "10A"
    }

ENHARMONIC_MAP = {
    "Db": "C#", "Eb": "D#", "Bb": "A#", "Ab": "G#", "Gb": "F#",
    "C#": "C#", "D#": "D#", "F#": "F#", "G#": "G#", "A#": "A#"
}
