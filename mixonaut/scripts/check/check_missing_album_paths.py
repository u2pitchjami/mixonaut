"""2025-08-20 - scripts de check si les données du host soient bien connues de beets."""

import argparse
import os
from os import PathLike
from datetime import datetime
from pathlib import Path

from mixonaut.beets_utils.commands.commands import get_beet_list
from mixonaut.utils.config import BEETS_MANUAL_LIST, MUSIC_BASE_PATH, BEETS_MUSIC
from mixonaut.utils.utils_div import ensure_to_path, ensure_to_str
from mixonaut.utils.logger import get_logger
from mixonaut.utils.safe_runner import safe_main

logger = get_logger("Check_Album_in_Beets")


def normalize_music_path(path: str | bytes | PathLike[str] | PathLike[bytes]) -> str:
    """
    Normalise un chemin musique pour comparaison relative.

    Exemples :
    /mnt/unraid/Musiques/Collection/Artist/Album -> Artist/Album
    /app/data/Artist/Album                      -> Artist/Album
    /Artist/Album                               -> Artist/Album
    """
    p = ensure_to_path(str(path))

    prefixes = (
        Path("/mnt/unraid/Musiques/Collection"),
        Path("/app/data"),
        Path("/music"),
        Path("/data"),
    )

    for prefix in prefixes:
        try:
            return p.relative_to(prefix).as_posix()
        except ValueError:
            continue

    return p.as_posix().lstrip("/")


def to_beets_import_path(album_key: str) -> str:
    """
    Convertit une clé album relative en chemin utilisable par Beets dans le conteneur.

    Exemple :
    Stevie Wonder/1979 - Album
    -> /app/data/Stevie Wonder/1979 - Album
    """
    return (Path(BEETS_MUSIC) / album_key).as_posix()


@safe_main
def check_missing_album_paths() -> None:
    """
    Verifie si les données du host sont bien connues de Beets.

    Cette fonction vérifie si tous les albums présents sur le disque sont également présents dans la base de datos de
    Beets. Si un album manquant est trouvé, il est ajouté à la liste manuelle de musique si celle-ci n'est pas définie.

    :return: Une liste des chemins d'albums manquants
    """
    logger.info(f"📅 CHECK PATHS IN BEETS : {datetime.now().strftime('%d-%m-%Y')}")
    logger.info("--- (vérifie si tous les albums sont biens connus de Beets) ---")

    music_base = Path(MUSIC_BASE_PATH)
    all_album_paths = [p for p in music_base.glob("*/*") if p.is_dir()]
    logger.info(f"📁 Albums trouvés sur disque : {len(all_album_paths)}")

    # expected_paths = {
    #     str(Path(BEETS_MUSIC) / p.relative_to(MUSIC_BASE_PATH)) for p in all_album_paths
    # }
    disk_album_paths = {
        normalize_music_path(path)
        for path in all_album_paths
        if ensure_to_str(path).strip()
    }
    # beet_output = get_beet_list("list", ["-a", "-f", "$path"], logger=logger)
    beet_output = get_beet_list(
        album=False, format=True, format_fields="$path", output_file=None, logger=logger
    )
    if beet_output is None:
        logger.error("❌ Impossible de récupérer la liste Beets.")
        return

    beet_album_paths = {
        normalize_music_path(Path(path).parent)
        for path in beet_output
        if ensure_to_str(Path(path)).strip()
    }

    missing = disk_album_paths - beet_album_paths

    missing_import_paths = [to_beets_import_path(key) for key in sorted(missing)]

    extra = sorted(beet_album_paths - disk_album_paths)
    logger.info(f"🛑 Albums absents de Beets : {len(missing)}")
    logger.info(f"✅ Albums supplémentaires dans Beets : {len(extra)}")

    if not missing:
        logger.info("✅ Tous les albums sont présents dans Beets.")
        return

    if BEETS_MANUAL_LIST:
        try:
            existing = set()
            if os.path.isfile(BEETS_MANUAL_LIST):
                with open(BEETS_MANUAL_LIST, encoding="utf-8") as f:
                    existing = {line.strip() for line in f if line.strip()}

            combined = sorted(existing.union(missing_import_paths))
            with open(BEETS_MANUAL_LIST, "w", encoding="utf-8") as f:
                for path in combined:
                    f.write(path + "\n")

            logger.info(
                f"📄 {len(missing_import_paths)} chemins ajoutés à la liste manuelle : {BEETS_MANUAL_LIST}"
            )
        except Exception as e:
            logger.error(f"❌ Erreur lors de l’écriture dans {BEETS_MANUAL_LIST} : {e}")
    else:
        logger.warning("Aucune variable BEETS_MANUAL_LIST définie.")

    logger.info("🏁 CHECK PATHS IN BEETS : TERMINE !! \n\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Détecte les albums manquant dans la base Beet."
    )
    args = parser.parse_args()
    check_missing_album_paths()
