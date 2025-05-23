from pathlib import Path
from utils.logger import get_logger
from utils.config import MANUAL_LIST, HOST_MUSIC, BEETS_MUSIC, WINDOWS_MUSIC
from db.access import execute_query
from logic.importer import build_track_dict, try_insert_track
from db.import_queries import fetch_beets_track_by_path
logger = get_logger("Import_Manuel")

def import_manual_tracks(like: bool = False):
    logger.info("📥 Lancement de l'import manuel via fichier .txt")
    paths = parse_manual_list(filepath=MANUAL_LIST, like=like)
    imported = 0

    for p in paths:
        row_data = fetch_beets_track_by_path(p)
        if not row_data:
            logger.warning(f"❌ Chemin introuvable dans Beets : {p}")
            continue

        track = build_track_dict(beet_id=None, row=row_data)
        if try_insert_track(track):
            imported += 1

    logger.info(f"✅ Import manuel terminé. Titres insérés : {imported}")


def parse_manual_list(filepath: str, like: bool = False) -> list[str]:
    """
    Lit un fichier .txt contenant des chemins vers des fichiers audio.
    Nettoie, convertit les chemins en version Beets (/app/data),
    et retourne une liste prête pour les requêtes SQL.
    
    :param filepath: Chemin vers le fichier texte.
    :param like: Si True, entoure les chemins de % pour les requêtes LIKE.
    """
    converted_paths = []

    try:
        if not MANUAL_LIST or not Path(MANUAL_LIST).is_file():
            logger.error(f"❌ Fichier manuel introuvable : {MANUAL_LIST}")
            return
    
        raw_lines = Path(filepath).read_text(encoding="utf-8").splitlines()
    except Exception as e:
        logger.error(f"❌ Erreur de lecture du fichier : {filepath} → {e}")
        return []

    for line in raw_lines:
        line = line.strip()
        if not line:
            continue

        path = None

        if line.startswith(HOST_MUSIC):
            relative = Path(line).relative_to(HOST_MUSIC)
            path = Path(BEETS_MUSIC) / relative

        elif line.startswith(WINDOWS_MUSIC):
            relative = Path(line.replace("W:\\Collection\\", "").replace("\\", "/"))
            path = Path(BEETS_MUSIC) / relative

        else:
            logger.warning(f"⚠️ Chemin non reconnu : {line}")
            continue

        path_str = str(path)
        if like:
            path_str = f"%{path_str}%"

        converted_paths.append(path_str)
        logger.debug(f"🔄 Chemin converti : {line} → {path_str}")

    return converted_paths