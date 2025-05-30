from datetime import datetime
import hashlib
from db.import_queries import insert_track
from utils.logger import get_logger
logname = __name__.split(".")[-1]
VALID_CAMELOT_KEYS = {f"{i}{k}" for i in range(1, 13) for k in ("A", "B")}

def compute_track_uid(title: str, artist: str) -> str:
    key = f"{title.strip().lower()}_{artist.strip().lower()}"
    return hashlib.md5(key.encode()).hexdigest()

def build_track_dict(beet_id: str, row: tuple, logname=logname) -> dict:
    """Construit un dict propre pour insertion à partir d’un row de Beets"""
    logger = get_logger(logname)
    try:
        title, artist, album, path, bpm, key, gain, genre, length = row
        return {
            "beet_id": beet_id,
            "track_uid": compute_track_uid(title, artist),
            "title": title,
            "artist": artist,
            "album": album,
            "path": path,
            "bpm": bpm,
            "key": key.strip().upper(),
            "rg_gain": gain,
            "genre": genre,
            "length": length,
            "added_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(timespec="seconds"),
            "present_in_beets": "1"
        }
    except Exception as e:
        logger.error(f"❌ [{__name__.split(".")[-1]}] Erreur dans la construction du dictionnaire → {e}")
        raise

def try_insert_track(track: dict, logname=logname) -> bool:
    """Insère un morceau s’il a une clé valide Camelot"""
    logger = get_logger(logname)
    key = track.get("key", "").strip().upper()
    if key not in VALID_CAMELOT_KEYS:
        logger.warning(f"⛔ Clé invalide Camelot : {track['artist']} - {track['title']} | key={key}")
        return False
    try:
        success = insert_track(track, logname=logname)
        if success:
            logger.info(f"✅ Insertion : {track['artist']} - {track['title']}")        
        
        return True
    except Exception as e:
        logger.warning(f"❌ [{__name__.split(".")[-1]}] Erreur insertion : {track['artist']} - {track['title']}")
        raise
