from datetime import datetime, timedelta
from collections import defaultdict
import argparse
import os
from beets_utils.commands import get_beet_list
from utils.config import BEETS_RECAP_DIR
from utils.logger import get_logger
logger = get_logger("Beets_recap")

def export_beet_snapshot():
    """
    Exporte un snapshot dans un dossier donné, avec un nom de fichier basé sur la date.
    Ex: beet_snapshot_2025-05-07.txt
    """
    dir_path = BEETS_RECAP_DIR
    os.makedirs(dir_path, exist_ok=True)

    date_str = datetime.now().strftime("%Y-%m-%d")
    filename = f"{date_str}_beet_snapshot.txt"
    file_path = os.path.join(dir_path, filename)

    get_beet_list(
        album=False,
        format_fields="$mtime|$added|$path",
        output_file=file_path,
        format=True,
        logname="Beets_recap"
    )

       
    logger.info(f"Snapshot exporté dans : {file_path}")

    return file_path  # utile pour l'utiliser directement après (ex: comparaison)


def load_snapshot(file_path: str) -> dict[str, tuple[str, str]]:
    data = {}
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split("|")
            if len(parts) != 3:
                continue
            mtime, added, path = [p.strip() for p in parts]
            data[path] = (mtime, added)
    return data

def generate_beet_change_log(old_file: str, new_file: str,) -> dict[str, list[str]]:
    old_data = load_snapshot(old_file)
    new_data = load_snapshot(new_file)
    date_str_new = new_file.removesuffix("_beet_snapshot.txt")
    date_str_old = old_file.removesuffix("_beet_snapshot.txt")
    logger.info(f"🔍 Comparaison de 🗓️ {date_str_new} avec 🗓️ {date_str_old}")
    added, modified, removed = [], [], []

    old_paths = set(old_data.keys())
    new_paths = set(new_data.keys())

    for path in new_paths - old_paths:
        added.append(path)

    for path in old_paths - new_paths:
        removed.append(path)

    for path in new_paths & old_paths:
        old_mtime = old_data[path][0]
        new_mtime = new_data[path][0]
        if new_mtime != old_mtime:
            modified.append(path)

    if not added and not modified and not removed:
        logger.info(f"🎹 Aucun mouvement sur la période")
    else:        
        logger.info(f"🟢 Nouveaux fichiers : {len(added)}")
        logger.info(f"🔄 Fichiers modifiés : {len(modified)}")
        logger.info(f"🔴 Fichiers supprimés : {len(removed)} \n")

    return {
        "added": added,
        "modified": modified,
        "removed": removed
    }

def auto_generate_beet_change_log(period: str = "all"):
    snapshots = get_last_two_snapshots(period)
    if not snapshots:
        raise ValueError("Pas assez de snapshots dans le dossier recap.")
    old_file, new_file = snapshots
    return generate_beet_change_log(old_file, new_file)

def get_last_two_snapshots(period: str = "all") -> tuple[str, str] | None:
    """
    Récupère les deux derniers fichiers snapshot dans le dossier BEETS_RECAP_DIR,
    filtrés selon la période : "all", "week", "month".
    Retourne un tuple (ancien, récent) ou None si pas assez de fichiers.
    """
    periode = "du jour"
    if period == "month":
        periode = "du mois"
    elif period == "week":
        periode = "de la semaine"
    logger.info(f"📰 RECAP {periode} :")
    now = datetime.now()
    files = []
    for f in os.listdir(BEETS_RECAP_DIR):
        if not f.endswith(".txt"):
            continue
        
        # Supposé : nom = YYYY-MM-DD_beet_snapshot.txt
        try:
            date_str = f.removesuffix("_beet_snapshot.txt")
            file_date = datetime.strptime(date_str, "%Y-%m-%d")            
        except ValueError:
            continue

        if period == "week" and (now - file_date).days > 7:
            continue
        if period == "month" and file_date.month != now.month:
            continue

        files.append((file_date, f))
    
    files = sorted(files)
    if len(files) < 2:
        return None

    old_file = os.path.join(BEETS_RECAP_DIR, files[-2][1])
    new_file = os.path.join(BEETS_RECAP_DIR, files[-1][1])
    return (old_file, new_file)


def regrouper_par_album(changements: dict[str, list[str]]) -> dict[str, set[str]]:
    """
    Regroupe les chemins de fichiers changés par dossier d'album.
    
    Retourne un dictionnaire :
    {
        "/chemin/album1": {"added"},
        "/chemin/album2": {"modified", "removed"},
    }
    """
    resultats = defaultdict(set)

    for type_changement, chemins in changements.items():
        for chemin in chemins:
            dossier_album = os.path.dirname(chemin)
            resultats[dossier_album].add(type_changement)

    return dict(resultats)

def export_change_log_markdown(album_changes: dict[str, set[str]], output_dir: str) -> str:
    """
    Exporte le résumé des changements par album dans un fichier Markdown.
    """
    os.makedirs(output_dir, exist_ok=True)

    date_str = datetime.now().strftime("%Y-%m-%d")
    filename = f"{date_str}_Beets_Recap.md"
    filepath = os.path.join(output_dir, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"# 📊 Changements Beets – {date_str}\n\n")

        grouped = defaultdict(list)
        for album_path, types in album_changes.items():
            for t in types:
                grouped[t].append(album_path)

        for t in sorted(grouped):
            emoji = {
                "added": "🟢",
                "modified": "🔄",
                "removed": "🔴"
            }.get(t, "📁")

            f.write(f"## {emoji} {t.capitalize()}\n\n")
            for path in sorted(grouped[t]):
                f.write(f"- `{path}`\n")
            f.write("\n")

    return filepath

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Vérifie que tous les albums Beet aient un mb_albumid")
    parser.add_argument("--period", choices=["week", "month", "all"], default="all", help="Période à analyser")
    parser.add_argument("--nosnapshot", action="store_true", help="Pas de Snapshot, juste le comparatif")
    parser.add_argument("--markdown", action="store_true", help="Génère un fichier markdown")
    args = parser.parse_args()

    logger.info(f"📅 BEETS RECAP : {datetime.now().strftime('%d-%m-%Y')}")
    if not args.nosnapshot:
        export_beet_snapshot()
    
    if args.period == "week":
        changements = auto_generate_beet_change_log(period="week")
    elif args.period == "month":
        changements = auto_generate_beet_change_log(period="month")
    else:
        changements = auto_generate_beet_change_log(period="all")
          
    if not all(not v for v in changements.values()):
        albums = regrouper_par_album(changements)
        logger.info(f"🎵 par Albums :")
        for dossier, types in sorted(albums.items()):
            resume = ", ".join(sorted(types))
            logger.info(f"📁 {dossier} ➜ {resume}")
    
    if args.markdown:
        markdown_path = export_change_log_markdown(albums, output_dir=BEETS_RECAP_DIR)
        logger.info(f"📝 Récap Markdown exporté : {markdown_path}")
        
    logger.info(f"🏁 BEETS RECAP : TERMINE !! \n\n")
    