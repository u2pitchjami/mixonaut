import os
import shutil
from utils.logger import get_logger
from utils.config import BEETS_CONFIG_MANUEL, BEETS_CONFIG_NORMAL, BEETS_CONFIG

def switch_config_to(mode_target: str, logname = __name__) -> str:
    """
    Bascule le fichier de config vers le mode spécifié (auto ou manuel),
    uniquement si ce n’est pas déjà le cas.

    Args:
        mode_target (str): 'auto' ou 'manuel'

    Returns:
        str: Le mode activé ou un message si rien n’a été fait
    """
    logger = getLogger(logname + "." + __name__)

    try:
        if mode_target not in {"auto", "manuel"}:
            logger.error("Mode invalide. Utilisez 'auto' ou 'manuel'.")
            return "erreur"

        # Déterminer le mode actuel
        if os.path.samefile(BEETS_CONFIG, BEETS_CONFIG_MANUEL):
            current_mode = "manuel"
        elif os.path.samefile(BEETS_CONFIG, BEETS_CONFIG_NORMAL):
            current_mode = "auto"
        else:
            logger.warning("Mode actuel non identifiable, on suppose 'auto'")
            current_mode = "auto"

        if current_mode == mode_target:
            logger.info(f"✅ Mode déjà actif : {mode_target}")
            return mode_target

        # Switch en fonction du mode demandé
        if mode_target == "manuel":
            shutil.move(BEETS_CONFIG, BEETS_CONFIG_NORMAL)
            shutil.move(BEETS_CONFIG_MANUEL, BEETS_CONFIG)
        else:  # mode_target == "auto"
            shutil.move(BEETS_CONFIG, BEETS_CONFIG_MANUEL)
            shutil.move(BEETS_CONFIG_NORMAL, BEETS_CONFIG)

        logger.info(f"✅ Mode {mode_target} activé")
        return mode_target

    except Exception as e:
        logger.error(f"❌ Erreur lors du switch : {e}")
        return "erreur"

