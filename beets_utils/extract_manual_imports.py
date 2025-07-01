import os
from datetime import datetime
from utils.config import BEETS_LOGS, BEETS_MANUAL_LIST
from utils.logger import get_logger, with_child_logger

@with_child_logger
def extract_manual_imports(logger = None):
    if not os.path.isfile(BEETS_LOGS):
        logger.warning(f"Fichier log introuvable : {BEETS_LOGS}")
        return
    try:
        with open(BEETS_LOGS, "r", encoding="utf-8") as f:
            lines = f.readlines()

        skipped = [line[5:].strip() for line in lines if line.startswith("skip ")]

        if skipped:
            with open(BEETS_MANUEL, "a", encoding="utf-8") as f_out:
                for entry in skipped:
                    f_out.write(entry + "\n")

            logger.info(f"[{datetime.now()}] - Albums à importer manuellement extraits : {len(skipped)}")
        else:
            logger.info("Aucun album à importer manuellement trouvé.")

        # Optionnel : suppression des doublons
        # on peut aussi ajouter un tri
        with open(BEETS_MANUEL, "r", encoding="utf-8") as f:
            unique_lines = sorted(set(line.strip() for line in f if line.strip()))

        with open(BEETS_MANUEL, "w", encoding="utf-8") as f:
            for line in unique_lines:
                f.write(line + "\n")

        # Vider le fichier de log beets
        open(BEETS_LOGS, "w", encoding="utf-8").close()

        logger.info(f"Fichier récap dispo dans : {BEETS_MANUEL}")

    except Exception as e:
        logger.error(f"Erreur durant l'extraction : {e}")

