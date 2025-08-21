from utils.logger import with_child_logger
import random
from utils.config import CAMELOT_ORDER, SEMITONE_SHIFT_VALUES
from db.analyse.transposition_queries import fetch_tracks_with_bpm_and_key, insert_transpositions
from utils.utils_div import format_nb, format_percent
from db.analyse.status_queries import update_table_status

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

# @with_child_logger
# def generate_transpositions(nb_limit=0, track_id=None, logger=None):
#     args_to_log = {k: v for k, v in locals().items() if k != "logger"}
#     logger.info("🔍 Démarrage de Process de Transposition")
#     logger.info("Arguments reçus : " + ", ".join([f"{k}={v}" for k, v in args_to_log.items()]))
    
#     rows = fetch_tracks_with_bpm_and_key(logger=logger)
#     if track_id:
#         filtered = [row for row in rows if row[0] == track_id]
#         if not filtered:
#             raise ValueError(f"Track ID {track_id} non trouvé dans les données.")
#         rows = filtered
                
#     total = nb_limit
    
#     if nb_limit == 0:
#         nb_limit = len(rows)
#         total = len(rows)
#     random.shuffle(rows)
#     logger.info(f"🎯 {format_nb(total, logger=logger)} morceaux à traiter")
#     count = 0
#     try:
#         for track_id, bpm, key in rows[:nb_limit]:
#             count += 1
#             logger.info(f"🔍 Traitement du morceau {track_id} - [{format_nb(count, logger=logger)}/{format_nb(total, logger=logger)}] ({format_percent(count, total, logger=logger)})")
#             keys, bpms = {}, {}
#             for shift in SEMITONE_SHIFT_VALUES:
#                 key_col = shift_to_colname("key", shift)
#                 bpm_col = shift_to_colname("bpm", shift)
#                 try:
#                     keys[key_col] = shift_camelot(key, shift, logger=logger)
#                     bpms[bpm_col] = shift_bpm(bpm, shift)
#                 except Exception as e:
#                     logger.warning("⛔ Erreur lors du shift %s pour track %s: %s", shift, track_id, e)
                    
#             insert_transpositions(track_id, keys, bpms)
            
#         logger.info(f"🏁 Terminé. {count} transpositions réalisées")
#     except Exception as e:
#         logger.error(f"❌ [{logger}] Erreur lors de la transposition : {e}")
#         raise
@with_child_logger
def generate_transpositions(nb_limit=0, track_id=None, logger=None):
    """
    Comportement:
      - Si track_id est fourni: traite 1 piste et retourne (data, err_code, err_msg)
      - Sinon (batch): traite jusqu'à nb_limit pistes et retourne ( {'processed': n}, None, None )
    """
    args_to_log = {k: v for k, v in locals().items() if k != "logger"}
    logger.info("🔍 Démarrage de Process de Transposition")
    logger.info("Arguments reçus : " + ", ".join([f"{k}={v}" for k, v in args_to_log.items()]))

    rows = fetch_tracks_with_bpm_and_key(logger=logger)

    # --- Mode single track (pour intégration post‑Essentia) ---
    if track_id:
        filtered = [row for row in rows if row[0] == track_id]
        if not filtered:
            #update_table_status("track_transpositions", track_id, err_code or "KO_UNSUPPORTED", err_msg, logger=logger)
            return None, "KO_UNSUPPORTED", f"Track ID {track_id} introuvable ou key/bpm manquants"
        tid, bpm, key = filtered[0]

        # Garde‑fous fonctionnels
        if key in (None, "", "no_key"):
            return None, "KO_UNSUPPORTED", f"initial_key inexploitable: {key}"
        if bpm is None or bpm <= 0:
            return None, "KO_UNSUPPORTED", f"BPM inexploitable: {bpm}"

        try:
            keys, bpms = {}, {}
            for shift in SEMITONE_SHIFT_VALUES:
                key_col = shift_to_colname("key", shift)
                bpm_col = shift_to_colname("bpm", shift)
                keys[key_col] = shift_camelot(key, shift, logger=logger)
                bpms[bpm_col] = shift_bpm(bpm, shift)

            insert_transpositions(tid, keys, bpms, logger=logger)
            # data de sortie utile si tu veux log/inspecter
            data = {"track_id": tid, "keys": keys, "bpms": bpms}
            return data, "OK", None

        except Exception as exc:  # pylint: disable=broad-except
            logger.exception("❌ Transposition: erreur technique pour track %s", track_id)
            return None, "KO_FILE", str(exc)

    # --- Mode batch (legacy CLI/cron) ---
    total = nb_limit if nb_limit > 0 else len(rows)
    if nb_limit == 0:
        nb_limit = len(rows)

    random.shuffle(rows)
    logger.info(f"🎯 {format_nb(total, logger=logger)} morceaux à traiter (batch)")
    count = 0
    try:
        for tid, bpm, key in rows[:nb_limit]:
            count += 1
            logger.info(
                "🔍 Traitement du morceau %s - [%s/%s] (%s)",
                tid,
                format_nb(count, logger=logger),
                format_nb(total, logger=logger),
                format_percent(count, total, logger=logger),
            )

            # Garde‑fous légers (en batch on continue sur la suivante)
            if key in (None, "", "no_key") or bpm is None or bpm <= 0:
                logger.warning("⛔ Transpo skip track %s (key=%s | bpm=%s)", tid, key, bpm)
                continue

            keys, bpms = {}, {}
            for shift in SEMITONE_SHIFT_VALUES:
                key_col = shift_to_colname("key", shift)
                bpm_col = shift_to_colname("bpm", shift)
                try:
                    keys[key_col] = shift_camelot(key, shift, logger=logger)
                    bpms[bpm_col] = shift_bpm(bpm, shift)
                except Exception as e:
                    logger.warning("⛔ Erreur shift %s pour track %s: %s", shift, tid, e)
            insert_transpositions(tid, keys, bpms, logger=logger)

        logger.info(f"🏁 Terminé. {count} transpositions réalisées")
        return {"processed": count}, None, None

    except Exception as e:
        logger.error("❌ [transpo] Erreur batch transposition : %s", e)
        raise
