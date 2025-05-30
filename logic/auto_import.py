from utils.logger import get_logger
from db.import_queries import fetch_beets_tracks_filtered
from logic.importer import build_track_dict, try_insert_track

logname = __name__.split(".")[-1]
logger = get_logger(logname)

def import_tracks_from_beets(count=0, logname=logname):
    """Importe les morceaux valides depuis Beets (automatique via genres EDM)"""
    logger.info("🚀 Lancement de l'import automatique depuis Beets")
    try:
        rows = fetch_beets_tracks_filtered()
        logger.info(f"🎧 Titres valides récupérés depuis Beets : {len(rows)}")
        if not rows:
            logger.warning("⚠️ Aucun morceau valide trouvé dans Beets")
            return
    
        inserted = 0
        for row in rows[:count]:
            beet_id, *data = row  # beet_id + reste
            track = build_track_dict(beet_id, data, logname=logname)

            if try_insert_track(track, logname=logname):
                inserted += 1
                logger.info(f"✅ Import terminé : {inserted} morceaux insérés")
    except Exception as e:
        logger.error(f"❌ [{__name__.split(".")[-1]}] Erreur lors de l'import : {e}")
        raise
