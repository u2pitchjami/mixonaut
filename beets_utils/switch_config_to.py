import os
from utils.logger import get_logger, with_child_logger
from utils.config import BEETS_CONFIG
import yaml

@with_child_logger
def switch_config_to(mode_target: str, logger=None) -> str:
    """
    Modifie le fichier de config Beets (config.yaml) pour activer le mode spécifié (auto ou manuel),
    uniquement si ce n’est pas déjà le cas.

    Args:
        mode_target (str): 'auto' ou 'manuel'

    Returns:
        str: Le mode activé ou un message si rien n’a été fait
    """
    try:
        if mode_target not in {"auto", "manuel"}:
            logger.error("Mode invalide. Utilisez 'auto' ou 'manuel'.")
            return "erreur"

        with open(BEETS_CONFIG, 'r') as f:
            config = yaml.safe_load(f)

        current_quiet = config.get('import', {}).get('quiet', False)
        current_timid = config.get('import', {}).get('timid', False)

        if mode_target == "auto":
            if current_quiet and not current_timid:
                logger.info("✅ Mode déjà actif : auto")
                return "auto"
            config['import']['quiet'] = True
            config['import']['timid'] = False

        elif mode_target == "manuel":
            if not current_quiet and current_timid:
                logger.info("✅ Mode déjà actif : manuel")
                return "manuel"
            config['import']['quiet'] = False
            config['import']['timid'] = True

        with open(BEETS_CONFIG, 'w') as f:
            yaml.safe_dump(config, f, default_flow_style=False)

        logger.info(f"✅ Mode {mode_target} activé")
        return mode_target

    except Exception as e:
        logger.error(f"❌ Erreur lors du switch : {e}")
        return "erreur"

