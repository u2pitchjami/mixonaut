"""2025-08-19 - module qui lance beet import."""

import os

from mixonaut.beets_utils.commands.commands import run_beet_command
from mixonaut.beets_utils.config.switch_config_to import switch_config_to
from mixonaut.utils.config import BEETS_IMPORT_PATH, BEETS_MANUAL_LIST
from mixonaut.utils.logger import LoggerProtocol, ensure_logger


def import_auto(
    noincremental: bool = False, logger: LoggerProtocol | None = None
) -> None:
    """
    Lance un import automatique de /app/imports après avoir :

    - sauvegardé la config Beets
    - activé le mode auto
    """
    logger = ensure_logger(logger, __name__)
    mode = switch_config_to(mode_target="auto", logger=logger)
    if mode != "auto":
        logger.warning("⚠️ Le switch en mode auto n’a pas fonctionné")
    if noincremental:
        logger.info("🔄 Import en mode noincremental activé")
        result = run_beet_command(
            "import",
            ["--noincremental", BEETS_IMPORT_PATH],
            interactive=True,
            logger=logger,
        )
    else:
        logger.info("🔄 Import en mode incrémental activé")
        result = run_beet_command(
            "import", [BEETS_IMPORT_PATH], interactive=True, logger=logger
        )

    if result is None:
        logger.error("❌ L'import automatique a échoué.")
    else:
        logger.info("✅ Import automatique terminé.")


def import_manuel(
    clear_after: bool = False,
    skip_only: bool = False,
    logger: LoggerProtocol | None = None,
) -> None:
    """
    Importe tous les dossiers listés dans BEETS_MANUAL_LIST, un par un, en mode manuel.

    - clear_after : vide le fichier une fois terminé
    - skip_only : n'importe que les entrées marquées [skip]
    """
    # backup = backup_beets_config()
    # if not backup:
    #     logger.warning("⚠️ Sauvegarde config échouée ou ignorée")
    logger = ensure_logger(logger, __name__)
    mode = switch_config_to("manuel", logger=logger)
    if mode != "manuel":
        logger.warning("⚠️ Le switch en mode manuel n’a pas fonctionné")

    if not BEETS_MANUAL_LIST or not os.path.isfile(BEETS_MANUAL_LIST):
        logger.warning("❌ Fichier manuel introuvable ou vide.")
        return

    with open(BEETS_MANUAL_LIST, encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]

    cleaned_lines = []
    for line in lines:
        if skip_only and not line.startswith("[skip]"):
            continue
        if line.startswith("[skip]") or line.startswith("[duplicate]"):
            path = line.split("]", 1)[1].strip()
        else:
            path = line  # fallback si ligne sans tag
        cleaned_lines.append(path)

    if not cleaned_lines:
        logger.info("✅ Aucun dossier à importer manuellement.")
        return

    for path in cleaned_lines:
        logger.info(f"📦 Import manuel : {path}")
        result = run_beet_command(
            "import", ["--noincremental", path], interactive=True, logger=logger
        )
        if result is None:
            logger.error(f"❌ Échec import : {path}")
        else:
            logger.info(f"✅ Import terminé : {path}")
            logger.info(f"✅ Import terminé : {result}")

    if clear_after:
        open(BEETS_MANUAL_LIST, "w", encoding="utf-8").close()
        logger.info(f"🧹 Fichier manuel vidé : {BEETS_MANUAL_LIST}")
