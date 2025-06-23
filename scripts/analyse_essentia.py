import argparse
from utils.logger import get_logger
from logic.sync_beets_from_essentia import sync_fields_by_track_id
from db.essentia_queries import fetch_tracks, nb_query, count_existing_features
from essentia.essentia_analyse import analyse_track
from logic.sync_beets_from_essentia import sync_fields_by_track_id
from utils.utils_div import format_nb, format_percent
from essentia.prep_essentia_analyse import generate_mode_text
from logic.transposition import generate_transpositions


logname = "Analyse_Essentia"
logger = get_logger(logname)

def main(force=False, count=0, missing_features=False, is_edm=False, missing_field=None, path_contains=None):
    logger.info("🔍 Démarrage analyse des morceaux via Essentia")
    try:
        total = fetch_tracks(missing_features=False, is_edm=is_edm, missing_field=missing_field, path_contains=path_contains, logname=logname)
        tracks = fetch_tracks(missing_features=missing_features, is_edm=is_edm, missing_field=missing_field, path_contains=path_contains, logname=logname)
        track_ids = [t[0] for t in total]
        existing = count_existing_features(track_ids)
        text = generate_mode_text(count=count, missing_features=missing_features, is_edm=is_edm, missing_field=missing_field, path_contains=path_contains)
        logger.info(f"🎯 [{text}]")
        logger.info(f"🎯 [{format_nb(existing)} titres déjà analysés sur un total de {format_nb(len(total))} --> {format_percent(existing, len(total))}]")

        if count == 0:
            count = len(tracks)

        if not tracks:
            logger.info("Aucun morceau à traiter")
            return
        
        for i, track in enumerate(tracks[:count], start=1):
            logger.info(f"▶️  [{format_nb(i)}/{format_nb(count)}] ({format_percent(i, count)}) Analyse : {track[0]} - {track[2]} - {track[3]} - {track[4]}")
                           
            track_features = analyse_track(track, force=force, source="Mixonaut", logname=logname)
            if track_features is None:
                logger.warning(f"❌ Analyse échouée pour le morceau : {track[0]}")
                continue
            logger.info(f"✅ Track mis à jour : {track[0]}")
            sync_fields_by_track_id(track_id=track[0], track_features=track_features, logname=logname)
            generate_transpositions(track_id=track[0], logname=logname)
            
            
        logger.info("🏁 Traitement terminé")
    except Exception as e:
        raise

if __name__ == "__main__":
    try:
        parser = argparse.ArgumentParser()
        parser.add_argument("--force", action="store_true", help="Forcer le recalcul même si les champs sont déjà remplis")
        parser.add_argument("--count", type=int, default=0, help="Nombre d'éléments à traiter (défaut: 0)")
        parser.add_argument("--missing-features", action="store_true")
        parser.add_argument("--is-edm", action="store_true")
        parser.add_argument("--missing-field", type=str)
        parser.add_argument("--path-contains", type=str)
        
        args = parser.parse_args()
        main(force=args.force, count=args.count, missing_features=args.missing_features, is_edm=args.is_edm, missing_field=args.missing_field, path_contains=args.path_contains)
    except Exception as e:
        raise