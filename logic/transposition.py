from utils.logger import get_logger
from utils.config import CAMELOT_ORDER, SEMITONE_SHIFT_VALUES
from db.transposition_queries import fetch_tracks_with_bpm_and_key, insert_transpositions
from db.db_utils import update_tracks_meta

logger = get_logger("Process_Transposition")

def shift_camelot(key: str, shift: int) -> str:
    try:
        index = CAMELOT_ORDER.index(key)
        return CAMELOT_ORDER[(index + shift) % 24]
    except ValueError:
        logger.warning("Clé Camelot inconnue : %s", key)
        raise

def shift_bpm(bpm: float, semitone_shift: int) -> float:
    ratio = 2 ** (semitone_shift / 12)
    return round(bpm * ratio, 2)

def shift_to_colname(prefix: str, shift: int) -> str:
    if shift == 0:
        return f"{prefix}_0"
    sign = "plus" if shift > 0 else "minus"
    return f"{prefix}_{sign}_{abs(shift)}"

def generate_transpositions(count=0):
    logger.info("🔍 Démarrage de Process de Transposition")
    rows = fetch_tracks_with_bpm_and_key()
    logger.info(f"🎯 {len(rows)} morceaux à traiter")
    try:
        for track_id, bpm, key in rows[:count]:
            print(f"🔍 Traitement du morceau {track_id} avec BPM: {bpm}, Key: {key}")
            keys, bpms = {}, {}
            for shift in SEMITONE_SHIFT_VALUES:
                key_col = shift_to_colname("key", shift)
                bpm_col = shift_to_colname("bpm", shift)
                try:
                    keys[key_col] = shift_camelot(key, shift)
                    bpms[bpm_col] = shift_bpm(bpm, shift)
                except Exception as e:
                    logger.warning("Erreur lors du shift %s pour track %s: %s", shift, track_id, e)
            insert_transpositions(track_id, keys, bpms, logname="Process_Transposition")
            #update_tracks_meta(track_id=track_id, logname="Process_Transposition")
        logger.info("Transpositions générées pour %d morceaux.", len(rows))
    except Exception as e:
        logger.error(f"❌ [{__name__.split(".")[-1]}] Erreur lors de la transposition : {e}")
        raise
