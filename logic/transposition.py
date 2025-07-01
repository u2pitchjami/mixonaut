from utils.logger import get_logger, with_child_logger
import random
from utils.config import CAMELOT_ORDER, SEMITONE_SHIFT_VALUES
from db.transposition_queries import fetch_tracks_with_bpm_and_key, insert_transpositions
from utils.utils_div import format_nb, format_percent

@with_child_logger
def shift_camelot(key: str, shift: int, logger=None) -> str:
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

@with_child_logger
def generate_transpositions(nb_limit=0, track_id=None, logger=None):
    args_to_log = {k: v for k, v in locals().items() if k != "logger"}
    logger.info("🔍 Démarrage de Process de Transposition")
    logger.info("Arguments reçus : " + ", ".join([f"{k}={v}" for k, v in args_to_log.items()]))
    
    rows = fetch_tracks_with_bpm_and_key(logger=logger)
    if track_id:
        filtered = [row for row in rows if row[0] == track_id]
        if not filtered:
            raise ValueError(f"Track ID {track_id} non trouvé dans les données.")
        rows = filtered
                
    total = nb_limit
    
    if nb_limit == 0:
        nb_limit = len(rows)
        total = len(rows)
    random.shuffle(rows)
    logger.info(f"🎯 {format_nb(total, logger=logger)} morceaux à traiter")
    count = 0
    try:
        for track_id, bpm, key in rows[:nb_limit]:
            count += 1
            logger.info(f"🔍 Traitement du morceau {track_id} - [{format_nb(count, logger=logger)}/{format_nb(total, logger=logger)}] ({format_percent(count, total, logger=logger)})")
            keys, bpms = {}, {}
            for shift in SEMITONE_SHIFT_VALUES:
                key_col = shift_to_colname("key", shift)
                bpm_col = shift_to_colname("bpm", shift)
                try:
                    keys[key_col] = shift_camelot(key, shift, logger=logger)
                    bpms[bpm_col] = shift_bpm(bpm, shift)
                except Exception as e:
                    logger.warning("⛔ Erreur lors du shift %s pour track %s: %s", shift, track_id, e)
                    
            insert_transpositions(track_id, keys, bpms)
            
        logger.info(f"🏁 Terminé. {count} transpositions réalisées")
    except Exception as e:
        logger.error(f"❌ [{logger}] Erreur lors de la transposition : {e}")
        raise
