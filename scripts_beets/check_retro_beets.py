from datetime import datetime
from beets_utils.commands import get_beet_list
from db.mixonaut_queries import fetch_data_in_mixonaut_by_beet_id
from scripts.analyse_essentia import analyse_track
from logic.write_tags import write_tags_docker
from beets_utils.update_beets_fields import update_beets_fields
from utils.utils_div import convert_path_format, add_updated_at
from utils.config import RETRO_MIXONAUT_BEETS
from utils.logger import get_logger

def check_mood_tags_in_beets(logname="Mixonaut", limit=None):
    logger = get_logger(logname)
    logger.info(f"🧠 CHECK ESSENTIA BEETS : {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}")
    logger.info("--- (identifie les morceaux sans champ `mood` dans Beets) ---")

    # Requête : mood vide ou non défini
    filters = " OR ".join(f"{field}::^$" for field in RETRO_MIXONAUT_BEETS)
    filters = f"({filters})"

    lines = get_beet_list(
        query="mood::^$",
        format=True,
        format_fields="$mb_trackid|$path|$albumartist|$album|$title|$id",
        logname="Check_Essentia_Beets"
    )
 
    if not lines:
        logger.info("🎉 Tous les morceaux ont un champ mood défini.")
        return

    logger.info(f"🟡 Nombre de morceaux sans mood : {len(lines)}")

    # Extraction et affichage des chemins/id
    for line in lines[:limit]:
        try:
            field_values = {}
            mb_trackid, path, artist, album, title, beet_id = [p.strip() for p in line.split("|")]
            logger.info(f"Test de la base Mixonaut - ID: {beet_id} | {path}")
            res = fetch_data_in_mixonaut_by_beet_id(fields=", ".join(RETRO_MIXONAUT_BEETS), beet_id=beet_id, logname="Check_Essentia_Beets")
            
            if res["status"] == "ok":
                logger.info(f" Données présentes dans Mixonaut")
                row = mixo_result["values"]
                field_values = dict(zip(RETRO_MIXONAUT_BEETS, row))
            else:
                logger.info("Mood vide ou inexistant.")
                track = tuple([p.strip() for p in line.split("|")])
                track_features=analyse_track(track=track, force=False, source="Beets")
                field_values = {field: track_features.get(field) for field in RETRO_MIXONAUT_BEETS}

            field_values = add_updated_at(field_values)
            logger.info(f"Mise à jour de la base Beets")
            update_beets_fields(
                    track_path=path,
                    logname="Retro_Beets_Db",
                    field_values=field_values
                )
                        
            new_path = convert_path_format(path=path, to_beets=False)
            logger.info(f"Ecriture des tags")
            write_tags_docker(path=new_path, track_features=field_values, tags_to_write=RETRO_MIXONAUT_BEETS, logname=logname)
            
        except ValueError:
            logger.warning(f"Ligne mal formatée : {line}")

    logger.info("🏁 Retro_Beets_Db : TERMINE \n")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=0, help="Nombre d'éléments à traiter (défaut: 0)")
        
    args = parser.parse_args()
    check_mood_tags_in_beets(logname="Retro_Beets_Db", limit=args.count)