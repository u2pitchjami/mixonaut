"""2025-08-20 - script de backup de la base beets."""

import os
import subprocess
import tarfile
from datetime import datetime
from pathlib import Path

from mixonaut.utils.config import (
    BEETS_BACKUP_DIR,
    BEETS_CONFIG_DIR,
    BEETS_DB,
    IMAGE_CLIENTS_DB,
)
from mixonaut.utils.logger import get_logger
from mixonaut.utils.safe_runner import safe_main


def sqlite_safe_backup(db_path: str, backup_dir: str) -> str:
    """
    Crée une copie atomique de la base SQLite via sqlite3 .backup en utilisant le conteneur clients_db.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    safe_db_copy = os.path.join(backup_dir, f"beets_db_{timestamp}.sqlite")

    cmd = [
        "docker",
        "run",
        "--rm",
        "-v",
        f"{os.path.abspath(os.path.dirname(db_path))}:/data",
        "-v",
        f"{os.path.abspath(backup_dir)}:/backups",
        "--entrypoint",
        "sqlite3",
        IMAGE_CLIENTS_DB,
        f"/data/{os.path.basename(db_path)}",
        f".backup '/backups/{os.path.basename(safe_db_copy)}'",
    ]

    try:
        subprocess.run(cmd, check=True)
        return safe_db_copy
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Erreur lors du backup SQLite : {e}")


@safe_main
def backup_beets_config():
    """
    Crée une archive .tar.gz du dossier de config Beets + DB SQLite sûre.
    """
    logger = get_logger("Beets_backup")

    if not BEETS_CONFIG_DIR or not os.path.isdir(BEETS_CONFIG_DIR):
        logger.error(f"❌ Dossier de config introuvable : {BEETS_CONFIG_DIR}")
        return None

    Path(BEETS_BACKUP_DIR).mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    archive_name = f"{timestamp}_beets_config.tar.gz"
    archive_path = os.path.join(BEETS_BACKUP_DIR, archive_name)

    # Étape 1 : backup SQLite sûr
    safe_db_copy = sqlite_safe_backup(BEETS_DB, BEETS_BACKUP_DIR)

    # Étape 2 : créer l’archive avec config + copie SQLite
    with tarfile.open(archive_path, "w:gz") as tar:
        tar.add(BEETS_CONFIG_DIR, arcname=os.path.basename(BEETS_CONFIG_DIR))
        tar.add(safe_db_copy, arcname=os.path.basename(safe_db_copy))

    # Étape 2bis : suppression de la copie SQLite temporaire
    try:
        os.remove(safe_db_copy)
        logger.info(f"🗑️ Fichier temporaire supprimé : {safe_db_copy}")
    except Exception as e:
        logger.warning(f"⚠️ Impossible de supprimer {safe_db_copy} : {e}")

        logger.info(f"✅ Backup complet créé : {archive_path}")
        return archive_path


if __name__ == "__main__":
    backup_beets_config()
