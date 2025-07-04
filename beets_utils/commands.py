import subprocess
import os
from utils.config import LOCK_FILE
from utils.logger import get_logger, with_child_logger
from beets_utils.beets_safe import safe_beets_call, read_lock_pid, get_current_pid

@with_child_logger
def run_beet_command(
    command: str,
    args: list[str] = None,
    capture_output: bool = True,
    check: bool = False,
    dry_run: bool = False,
    logger: str = None
) -> dict:
    """
    Exécute une commande Beets de façon sûre et loggée.

    Args:
        command (str): Commande Beets de base (ex: 'list', 'remove', 'update').
        args (list[str], optional): Liste des arguments (ex: ['-f', '$title', 'artist::Daft Punk']).
        capture_output (bool): Capture ou non la sortie.
        check (bool): Lève une exception si code retour ≠ 0.

    Returns:
        str | None: Résultat stdout si capturé, sinon None.
    """
    cmd = ["beet", "-v", command]
    if args and all(arg is not None for arg in args):
        cmd.extend(args)
       
    if dry_run:
        logger.info(f"[SIMULATION] {' '.join(cmd)}")
        return
    
    try:
        if safe_beets_call(logger=logger):
            logger.debug(f"🔧 Exécution Beets : {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                text=True,
                check=check,
                capture_output=capture_output
            )
            if capture_output:
                return {
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip(),
                "returncode": result.returncode
                }
                
            return None

    except Exception as e:
        logger.error(f"Erreur beet : {e}")
        return {
            "stdout": e.stdout.strip() if e.stdout else "",
            "stderr": e.stderr.strip() if e.stderr else str(e),
            "returncode": e.returncode
        }
    finally:
        if read_lock_pid() == get_current_pid():
                os.remove(LOCK_FILE)
                logger.debug("🔓 Verrou supprimé.")
        else:
            logger.warning("⚠️ Tentative de suppression du verrou non possédé (ignorée).")

@with_child_logger
def run_beet_action_by_dirs(action, dirs, dry_run=False, logger=None):
    if not dirs:
        return
    for album_dir in sorted(dirs):
        if dry_run:
            logger.info(f"[SIMULATION] {action} sur dossier : {album_dir}")
        else:
            try:
                #subprocess.run(["beet", action, album_dir], check=True)
                run_beet_command(command=action, args=[album_dir], capture_output=False, dry_run=dry_run, logger=logger)
                logger.info(f"[FIX] {action} appliqué sur : {album_dir}")
            except subprocess.CalledProcessError:
                logger.warning(f"[ERREUR] {action} échoué sur : {album_dir}")

@with_child_logger
def get_beet_list(
    query: str = None,
    format_fields: str = "$title|$genre|$rg_track_gain|$initial_key|$bpm|$path",
    output_file: str = None,
    logger: str = None,
    album: bool = False,
    format: bool = False
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
    args = []

    if album:
        args.append("-a")
    if format:
        args.extend(["-f", format_fields])
    if query:
        args.append(query)

    #logger.info(f"Commande Beet : beet list {' '.join(args)}")
    try:
        result = run_beet_command(command="list", args=args, capture_output=True, dry_run=False, logger=logger)
        stdout = result.get("stdout", "")
        lines = [line.strip() for line in stdout.splitlines() if line.strip()]
        
        if output_file:
            try:
                with open(output_file, "w", encoding="utf-8") as f:
                    f.write("\n".join(lines))
                #logger.info(f"{len(lines)} lignes sauvegardées dans {output_file}")
            except Exception as e:
                logger.error(f"Erreur lors de l'écriture du fichier : {e}")

        return lines

    except subprocess.CalledProcessError as e:
        logger.error("Erreur lors de l'exécution de 'beet list'")
        logger.error(e.stderr.strip() if e.stderr else str(e))
        return []
