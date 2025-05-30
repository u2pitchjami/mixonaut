from datetime import datetime
from beets_utils.commands import get_beet_list
from db.mixonaut_queries import fetch_data_in_mixonaut_by_beet_id
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
            mb_trackid, path, artist, album, title, beet_id = [p.strip() for p in line.split("|")]
            logger.info(f"🧪 Traitement : ID {beet_id} | {path}")
            sync_beets_from_mixonaut(beet_id=beet_id, path=path, line_fallback=line, logname=logname)
        except ValueError:
            logger.warning(f"⚠️ Ligne mal formatée : {line}")

            
def sync_beets_from_mixonaut(
    beet_id: str,
    path: str,
    line_fallback: str = None,
    *,
    artist=None, album=None, title=None, mb_trackid=None,
    logname="Retro_Beets_Db"
) -> None:
    logger = get_logger(logname)
    
    res = fetch_data_in_mixonaut_by_beet_id(
        fields=", ".join(RETRO_MIXONAUT_BEETS.keys()),
        beet_id=beet_id,
        logname=logname
    )

    if res["status"] == "ok":
        row = res["values"]
        logger.info(f"🔁 Données trouvées dans Mixonaut")
        field_values = {
            RETRO_MIXONAUT_BEETS[mixo_field]: value
            for mixo_field, value in zip(RETRO_MIXONAUT_BEETS.keys(), row)
        }
    else:
        logger.info("🔍 Aucune donnée → lancement analyse Essentia")
        from scripts.analyse_essentia import analyse_track
        if line_fallback:
            track = tuple([p.strip() for p in line_fallback.split("|")])
        else:
            track = (mb_trackid or "", path or "", artist or "", album or "", title or "", beet_id or "")

        track_features = analyse_track(track=track, force=False, source="Beets")

        field_values = {
            RETRO_MIXONAUT_BEETS[mixo_field]: track_features.get(mixo_field)
            for mixo_field in RETRO_MIXONAUT_BEETS
        }

    field_values = add_updated_at(field_values)
    path = path.decode("utf-8") if isinstance(path, bytes) else path
    logger.info(f"💾 Mise à jour de la base Beets field_values {field_values}")
    try:
        update_beets_fields(
            track_path=path,
            logname=logname,
            field_values=field_values
        )
    except Exception as e:
        logger.error(f"❌ Erreur lors de la mise à jour des champs Beets : {e}")
        raise
    
    print(f"Track ID: {beet_id}, Path: {path}, Artist: {artist}, Album: {album}, Title: {title}")
    new_path = convert_path_format(path=path, to_beets=False)
    print(f"🔄 Nouveau chemin converti : {new_path}")
    logger.info("🏷️ Ecriture des tags")
    write_tags_docker(
        path=new_path,
        track_features=field_values,
        tags_to_write=set(RETRO_MIXONAUT_BEETS.values()),
        logname=logname
    )

    logger.info("🏁 Retro_Beets_Db : TERMINE \n")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=0, help="Nombre d'éléments à traiter (défaut: 0)")
        
    args = parser.parse_args()
    check_mood_tags_in_beets(logname="Retro_Beets_Db", limit=args.count)