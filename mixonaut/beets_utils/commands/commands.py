"""
Lanceur de commandes beets.
"""

from __future__ import annotations

import os
import subprocess
import sys

from mixonaut.beets_utils.lock.beets_safe import (
    get_current_pid,
    read_lock_pid,
    safe_beets_call,
)
from mixonaut.utils.config import LOCK_FILE
from mixonaut.utils.logger import LoggerProtocol, ensure_logger
from mixonaut.utils.types import ProcessResult


def run_beet_command(
    command: str,
    args: list[str] | None = None,
    interactive: bool = False,
    check: bool = False,
    dry_run: bool = False,
    logger: LoggerProtocol | None = None,
) -> ProcessResult:
    """
    Exécute une commande Beets de façon sûre et loggée.
    """
    logger = ensure_logger(logger, __name__)
    cmd = ["beet", command]
    if args and all(arg is not None for arg in args):
        cmd.extend(args)

    if dry_run:
        logger.info("[SIMULATION] %s", " ".join(cmd))
        return {"stdout": "", "stderr": "", "returncode": 0}

    try:
        if not safe_beets_call(logger=logger):
            # Cas où l'appel est volontairement bloqué (lock, préconditions, etc.)
            logger.warning("Appel Beets ignoré (préconditions non satisfaites).")
            return {
                "stdout": "",
                "stderr": "Skipped: preconditions not met.",
                "returncode": 2,
            }

        logger.debug(f"🔧 Exécution Beets : {' '.join(cmd)}")

        if interactive:
            completed = subprocess.run(
                cmd,
                text=True,
                check=check,
                stdin=sys.stdin,
                stdout=sys.stdout,
                stderr=sys.stderr,
            )
            rc = getattr(completed, "returncode", 0)
            return {"stdout": "", "stderr": "", "returncode": rc}

        else:
            completed = subprocess.run(cmd, text=True, check=check, capture_output=True)
            return {
                "stdout": (completed.stdout or "").strip(),
                "stderr": (completed.stderr or "").strip(),
                "returncode": completed.returncode,
            }

    except subprocess.CalledProcessError as exc:
        logger.error("Erreur beet (CalledProcessError) : %s", exc)
        return {
            "stdout": (getattr(exc, "stdout", "") or "").strip(),
            "stderr": (getattr(exc, "stderr", str(exc)) or "").strip(),
            "returncode": getattr(exc, "returncode", 1),
        }
    except Exception as exc:  # noqa: BLE001
        logger.exception("Erreur inattendue durant l'exécution Beets : %s", exc)
        return {"stdout": "", "stderr": str(exc), "returncode": 1}

    finally:
        if read_lock_pid() == get_current_pid():
            os.remove(LOCK_FILE)
            logger.debug("🔓 Verrou supprimé.")
        else:
            logger.warning(
                "⚠️ Tentative de suppression du verrou non possédé (ignorée)."
            )


#
# def run_beet_action_by_dirs(action, dirs, dry_run=False, logger=None):
#     if not dirs:
#         return
#     for album_dir in sorted(dirs):
#         if dry_run:
#             logger.info(f"[SIMULATION] {action} sur dossier : {album_dir}")
#         else:
#             try:
#                 #subprocess.run(["beet", action, album_dir], check=True)
#                 run_beet_command(command=action, args=[album_dir], interactive=False, dry_run=dry_run, logger=logger)
#                 logger.info(f"[FIX] {action} appliqué sur : {album_dir}")
#             except subprocess.CalledProcessError:
#                 logger.warning(f"[ERREUR] {action} échoué sur : {album_dir}")


def get_beet_list(
    query: str | None = None,
    format_fields: str = "$title|$genre|$rg_track_gain|$initial_key|$bpm|$path",
    output_file: str | None = None,
    logger: LoggerProtocol | None = None,
    album: bool = False,
    format: bool = False,
) -> list[str]:
    """
    Exécute une commande `beet list` avec format et filtre personnalisés.

    :param query: Chaîne de requête Beets (ex: 'artist::Daft Punk')
    :param format_fields: Format des champs Beets (ex: '$title|$bpm|$path')
    :param output_file: Si fourni, écrit la sortie dans ce fichier
    :param logger: Nom du logger à utiliser
    :param album: Active le mode album (-a) si True
    :param format: Active le format personnalisé (-f) si True
    :return: Liste des lignes retournées
    """
    logger = ensure_logger(logger, __name__)
    args = []

    if album:
        args.append("-a")
    if format:
        args.extend(["-f", format_fields])
    if query:
        args.append(query)

    # logger.info(f"Commande Beet : beet list {' '.join(args)}")
    try:
        out: ProcessResult = run_beet_command(
            command="list", args=args, interactive=False, dry_run=False, logger=logger
        )
        stdout = out["stdout"]

        lines = [line.strip() for line in stdout.splitlines() if line.strip()]

        if output_file:
            try:
                with open(output_file, "w", encoding="utf-8") as f:
                    f.write("\n".join(lines))
                # logger.info(f"{len(lines)} lignes sauvegardées dans {output_file}")
            except Exception as e:
                logger.error(f"Erreur lors de l'écriture du fichier : {e}")

        return lines

    except subprocess.CalledProcessError as e:
        logger.error("Erreur lors de l'exécution de 'beet list'")
        logger.error(e.stderr.strip() if e.stderr else str(e))
        return []
