import argparse
from utils.logger import get_logger
from logic.sync_beets_from_essentia import sync_fields_by_track_id
from db.essentia_queries import fetch_tracks, nb_query
from essentia.essentia_analyse import analyse_track
from logic.sync_beets_from_essentia import sync_fields_by_track_id



logname = "Analyse_Essentia"
logger = get_logger(logname)

def main(force=False, count=0):
    logger.info("🔍 Démarrage analyse des morceaux via Essentia")
    try:
        tracks = fetch_tracks(missing_features=True)
        nb = nb_query(table="audio_features")
        logger.info(f"🎯 {nb} titres déjà analysés sur un total de {len(tracks)}")
        if not tracks:
            logger.info("Aucun morceau à traiter")
            return
        
        for track in tracks[:count]:
            track_features = analyse_track(track, force=force, source="Mixonaut", logname=logname)
            logger.info(f"✅ Track mis à jour : {track[0]}")
            sync_fields_by_track_id(track_id=track[0], track_features=track_features, logname=logname)
            
        logger.info("🏁 Traitement terminé")
    except Exception as e:
        raise

if __name__ == "__main__":
    try:
        parser = argparse.ArgumentParser()
        parser.add_argument("--force", action="store_true", help="Forcer le recalcul même si les champs sont déjà remplis")
        parser.add_argument("--count", type=int, default=0, help="Nombre d'éléments à traiter (défaut: 0)")
        parser.add_argument("--missing-features", action="store_true")
        parser.add_argument("--missing-field", type=str)
        parser.add_argument("--path-contains", type=str)
        
        args = parser.parse_args()
        main(force=args.force, count=args.count)
    except Exception as e:
        raise