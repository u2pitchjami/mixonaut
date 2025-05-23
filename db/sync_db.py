# sync_presence.py

from utils.logger import get_logger
from utils.config import BEETS_DB, MIX_DB
from db.access import execute_query


def mark_missing_tracks(logname="Mixonaut"):
    logger = get_logger(logname)
    logger.info("Début de la vérification de présence entre Beets et Mixonaut")

    # Récupérer tous les beet_id de Mixonaut
    query_get_mixonaut_ids = "SELECT beet_id FROM tracks WHERE beet_id IS NOT NULL"
    mixonaut_ids = execute_query(query_get_mixonaut_ids, fetch=True, db=MIX_DB)
    mixonaut_ids = [row[0] for row in mixonaut_ids]

    logger.info(f"{len(mixonaut_ids)} beet_id trouvés dans la base Mixonaut")

    # Requête préparée pour tester la présence dans Beets
    query_check_beets = "SELECT 1 FROM items WHERE id = ? LIMIT 1"

    missing_ids = []

    for beet_id in mixonaut_ids:
        result = execute_query(query_check_beets, params=(beet_id,), fetch=True, db=BEETS_DB)
        if not result:
            missing_ids.append(beet_id)

    logger.info(f"{len(missing_ids)} beet_id absents de Beets")

    # Mise à jour des entrées manquantes dans Mixonaut
    for beet_id in missing_ids:
        update_query = "UPDATE tracks SET present_in_beets = 0 WHERE beet_id = ?"
        execute_query(update_query, params=(beet_id,), db=MIX_DB)
        logger.debug(f"Marqué absent : beet_id={beet_id}")

    logger.info("Synchronisation des absents terminée.")

# sync_paths.py
def sync_paths(logname="Mixonaut"):
    logger = get_logger(logname)
    logger.info("Début de la synchronisation des chemins entre Beets et Mixonaut")

    # Récupération des morceaux actifs dans Mixonaut
    query_get_tracks = """
        SELECT beet_id, path FROM tracks
        WHERE beet_id IS NOT NULL AND present_in_beets = 1
    """
    tracks = execute_query(query_get_tracks, fetch=True, db=MIX_DB)

    logger.info(f"{len(tracks)} morceaux à vérifier")

    query_get_path_beets = "SELECT path FROM items WHERE id = ?"

    updates_count = 0

    for beet_id, mixonaut_path in tracks:
        result = execute_query(query_get_path_beets, params=(beet_id,), fetch=True, db=BEETS_DB)

        if not result:
            logger.warning(f"Aucune entrée Beets pour beet_id={beet_id}, ignoré")
            continue

        beets_path = result[0][0]

        if mixonaut_path != beets_path:
            logger.info(f"🔄 Mise à jour path beet_id={beet_id} :\n → Mixonaut: {mixonaut_path}\n → Beets:    {beets_path}")
            update_query = "UPDATE tracks SET path = ? WHERE beet_id = ?"
            execute_query(update_query, params=(beets_path, beet_id), db=MIX_DB)
            updates_count += 1

    logger.info(f"Synchronisation terminée. {updates_count} chemins mis à jour.")


def check_technical_differences(logname="Mixonaut"):
    logger = get_logger(logname)
    logger.info("Début de la vérification des divergences techniques (BPM, key, rg_gain)")

    # On se limite aux morceaux encore présents dans Beets
    query_get_tracks = """
        SELECT beet_id, bpm, key, rg_gain FROM tracks
        WHERE beet_id IS NOT NULL AND present_in_beets = 1
    """
    tracks = execute_query(query_get_tracks, fetch=True, db=MIX_DB)

    logger.info(f"{len(tracks)} morceaux à comparer techniquement")

    query_get_beets_data = "SELECT bpm, initial_key, rg_track_gain FROM items WHERE id = ?"

    for beet_id, bpm_mix, key_mix, rg_mix in tracks:
        result = execute_query(query_get_beets_data, params=(beet_id,), fetch=True, db=BEETS_DB)

        if not result:
            logger.warning(f"beet_id {beet_id} non trouvé dans Beets, ignoré")
            continue

        bpm_beets, key_beets, rg_beets = result[0]

        # Normalisation des formats
        bpm_mix = round(float(bpm_mix), 1) if bpm_mix is not None else None
        bpm_beets = round(float(bpm_beets), 1) if bpm_beets is not None else None

        rg_mix = round(float(rg_mix), 1) if rg_mix is not None else None
        rg_beets = round(float(rg_beets), 1) if rg_beets is not None else None

        key_mix = key_mix.upper() if key_mix else None
        key_beets = key_beets.upper() if key_beets else None

        if bpm_mix != bpm_beets or key_mix != key_beets or rg_mix != rg_beets:
            logger.info(
                f"Divergence beet_id={beet_id} | BPM: {bpm_mix} vs {bpm_beets} | "
                f"Key: {key_mix} vs {key_beets} | RG: {rg_mix} vs {rg_beets}"
            )

    logger.info("Fin de la vérification des divergences techniques")
