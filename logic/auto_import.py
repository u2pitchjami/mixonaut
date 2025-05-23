from utils.logger import get_logger
from db.import_queries import fetch_beets_tracks_filtered
from logic.importer import build_track_dict, try_insert_track


logger = get_logger("Import_Auto")

def import_tracks_from_beets():
    """Importe les morceaux valides depuis Beets (automatique via genres EDM)"""
    logger.info("🚀 Lancement de l'import automatique depuis Beets")

    rows = fetch_beets_tracks_filtered()
    logger.info(f"🎧 Titres valides récupérés depuis Beets : {len(rows)}")

    inserted = 0
    for row in rows[:100]:
        beet_id, *data = row  # beet_id + reste
        track = build_track_dict(beet_id, data)

        if try_insert_track(track):
            inserted += 1

    logger.info(f"✅ Import terminé : {inserted} morceaux insérés")
