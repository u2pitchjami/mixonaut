import tarfile
import argparse
from datetime import datetime
from pathlib import Path
import os
from utils.config import BEETS_CONFIG_DIR, BEETS_BACKUP_DIR
from utils.logger import get_logger

def backup_beets_config():
    """
    Crée une archive .tar.gz du dossier de configuration Beets avec timestamp.
    """        
    logger = get_logger("Beets_backup")
        
    # if args.logname:
    #     logger = logging.getLogger(logname + "." + "backup")
    #     print (logger)
    # else:
    #     from utils.logger import get_logger
    #     logging.basicConfig(level=logging.DEBUG)
    #     get_logger("beets_backup")
    #     logger = logging.getLogger("beets_backup")
    #     print (logger)
    # logger.info(f"✅ hello")       
    if not BEETS_CONFIG_DIR or not os.path.isdir(BEETS_CONFIG_DIR):
        logger.error(f"❌ Dossier de config introuvable : {BEETS_CONFIG_DIR}")
        return None

    Path(BEETS_BACKUP_DIR).mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    archive_name = f"{timestamp}_beets_config.tar.gz"
    archive_path = os.path.join(BEETS_BACKUP_DIR, archive_name)

    try:
        with tarfile.open(archive_path, "w:gz") as tar:
            tar.add(BEETS_CONFIG_DIR, arcname=os.path.basename(BEETS_CONFIG_DIR))
        logger.info(f"✅ Backup créé : {archive_path}")
        return archive_path

    except Exception as e:
        logger.error(f"❌ Erreur lors de la création de l'archive : {e}")
        return None

if __name__ == "__main__":
    # parser = argparse.ArgumentParser(description="SAV du dossier config de Beets")
    # parser.add_argument("--logname", default=None, help="log source")
    # args = parser.parse_args()
    # print(args.logname)
    backup_beets_config()