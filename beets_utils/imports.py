import os
from scripts_beets.backup_beets_config import backup_beets_config
from beets_utils.switch_config_to import switch_config_to
from beets_utils.commands import run_beet_command
from utils.config import BEETS_MANUAL_LIST, BEETS_IMPORT_PATH
from utils.logger import get_logger, with_child_logger

@with_child_logger
def import_auto(logger = None):
    """
    Lance un import automatique de /app/imports après avoir :
    - sauvegardé la config Beets
    - activé le mode auto
    """
    backup = backup_beets_config()
    if not backup:
        logger.warning("⚠️ Sauvegarde config échouée ou ignorée")

    mode = switch_config_to("auto")
    if mode != "auto":
        logger.warning("⚠️ Le switch en mode auto n’a pas fonctionné")

    result = run_beet_command("import", [BEETS_IMPORT_PATH], capture_output=True, logger=logger)
    #print(result)
    if result is None:
        logger.error("❌ L'import automatique a échoué.")
    else:
        logger.info("✅ Import automatique terminé.")

@with_child_logger
def import_manuel(clear_after=True, logger = None):
    """
    Importe tous les dossiers listés dans BEETS_MANUAL_LIST, un par un, en mode manuel.
    """
    backup = backup_beets_config()
    if not backup:
        logger.warning("⚠️ Sauvegarde config échouée ou ignorée")

    mode = switch_config_to("manuel")
    if mode != "manuel":
        logger.warning("⚠️ Le switch en mode manuel n’a pas fonctionné")

    if not BEETS_MANUAL_LIST or not os.path.isfile(BEETS_MANUAL_LIST):
        logger.warning("❌ Fichier manuel introuvable ou vide.")
        return

    with open(BEETS_MANUAL_LIST, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]

    if not lines:
        logger.info("✅ Aucun dossier à importer manuellement.")
        return

    for path in lines:
        logger.info(f"📦 Import manuel : {path}")
        result = run_beet_command("import", [path], capture_output=False)
        if result is None:
            logger.error(f"❌ Échec import : {path}")
        else:
            logger.info(f"✅ Import terminé : {path}")

    if clear_after:
        open(BEETS_MANUAL_LIST, "w", encoding="utf-8").close()
        logger.info(f"🧹 Fichier manuel vidé : {BEETS_MANUAL_LIST}")