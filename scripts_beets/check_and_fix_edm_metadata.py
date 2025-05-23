import subprocess
import argparse
from datetime import datetime
import os
from utils.config import EDM_GENRES
from beets_utils.check_and_fix_utils import is_missing_genre, is_missing_gain, is_missing_bpm, is_missing_key
from beets_utils.commands import run_beet_action_by_dirs, get_beet_list, run_beet_command
from utils.logger import get_logger
logger = get_logger("Check_EDM")

def check_edm_metadata(artist=None, dry_run=False):
    logger.info(f"📅 CHECK EDM METADATAS : {datetime.now().strftime('%d-%m-%Y')}")
    
    lines = get_beet_list(query=artist, album=False, format=True, format_fields="$genre|$path", logname="Check_EDM")
    if not lines:
        return

    logger.info(f"--- Nombre de titres à contrôler : {len(lines)} ---")
    # Étape 1 : détecter les albums sans genre
    dirs_without_genre = set()
    all_album_dirs = set()

    for line in lines:
        parts = line.split("|")
        
        if len(parts) != 2:
            continue
        genre, path = [p.strip() for p in parts]
                
        album_dir = os.path.dirname(path)
        all_album_dirs.add(album_dir)
        genre_ok = is_missing_genre(genre.lower())
    
        
        if not genre_ok:
            dirs_without_genre.add(album_dir)
            continue

    if dirs_without_genre:
        logger.warning(f"⚠️ Albums avec au moins un titre sans genre : {len(dirs_without_genre)}")
        for d in sorted(dirs_without_genre):
            logger.warning(f" - {d}")
            logger.info("🛠 Lancement de 'beet autogenre' uniquement sur les albums concernés...")
            try:
                run_beet_command(command="autogenre", args=["-af", d], dry_run=dry_run, logname="Check_EDM")
                
                logger.info(f"[FIX] ⚡ autogenre appliqué sur : {d}")
            except subprocess.CalledProcessError:
                logger.warning(f"[ERREUR] autogenre échoué sur : {d}")    

        # Recharger les lignes après autogenre
        #lines = get_beet_list(artist)
        lines = get_beet_list(query=artist, album=False, format=True, format_fields="$title|$genre|$rg_track_gain|$initial_key|$bpm|$path", logname="Check_EDM")
        remaining_genreless = set()
        for line in lines:
            parts = line.split("|")
            if len(parts) != 6:
                continue
            _, genre, _, _, _, path = [p.strip() for p in parts]
            #album_dir = os.path.dirname(path)
            genre_ok = is_missing_genre(genre)
            if not genre_ok:
                dirs_without_genre.add(path)
                
        if path in dirs_without_genre and (not genre or genre.lower() in {"", "unknown", "none", "?"}):
            logger.warning(f"⚠️ Albums avec au moins un titre sans genre : {len(dirs_without_genre)}")
            remaining_genreless.add(path)

        if remaining_genreless:
            logger.warning("⚠️ Albums toujours sans genre après autogenre (à traiter manuellement) :")
            for d in sorted(remaining_genreless):
                logger.warning(f" - {d}")

    # Étape 2 : analyse complète pour BPM / gain / key
    missing_data = []
    dirs_to_fix = {
        "replaygain": set(),
        "keyfinder": set(),
        "bpm": set()
    }

    for line in lines:
        parts = line.split("|")
        if len(parts) != 6:
            continue
        title, genre, rg_gain, key, bpm, path = [p.strip() for p in parts]
        album_dir = os.path.dirname(path)

        if not genre or not any(sub in genre.lower() for sub in EDM_GENRES):
            continue

        missing = {
            "rg": is_missing_gain(rg_gain),
            "key": is_missing_key(key),
            "bpm": is_missing_bpm(bpm)
        }

        if any(missing.values()):
            missing_data.append((title, genre, rg_gain, key, bpm, path))
            if missing["rg"]:
                dirs_to_fix["replaygain"].add(album_dir)
            if missing["key"]:
                dirs_to_fix["keyfinder"].add(album_dir)
            if missing["bpm"]:
                dirs_to_fix["bpm"].add(album_dir)

    if not missing_data:
        logger.info("✅ Tous les morceaux EDM ont les métadonnées requises.")
    else:
        for title, genre, rg, key, bpm, path in missing_data:
            logger.info(f"[INCOMPLET] {title} | Genre: {genre} | Gain: {rg or '🚨'} | Key: {key or '🚨'} | BPM: {bpm or '🚨'}")
            logger.info(f"            ↳ {path}")
        logger.info("--- 💊 Application des corrections par dossier album ---")

    # Appliquer les actions de correction
    run_beet_action_by_dirs("replaygain", dirs_to_fix["replaygain"], dry_run, logname="Check_EDM")
    run_beet_action_by_dirs("keyfinder", dirs_to_fix["keyfinder"], dry_run, logname="Check_EDM")
    run_beet_action_by_dirs("autobpm", dirs_to_fix["bpm"], dry_run, logname="Check_EDM")

    logger.info(f"🏁 CHECK EDM METADATAS : TERMINE !! \n\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Vérifie et corrige RG/BPM/KEY pour les titres EDM")
    parser.add_argument("--artist", help="Limiter à un artiste spécifique (facultatif)")
    parser.add_argument("--dry-run", action="store_true", help="N'applique pas les modifications (simulation)")
    args = parser.parse_args()

    check_edm_metadata(artist=args.artist, dry_run=args.dry_run)
