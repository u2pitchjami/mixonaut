"""
2025-08-20.

module qui gère le lock de la base car sqlite ne supporte qu'une seule connection.
"""

from __future__ import annotations

import os
import re
import time
from datetime import datetime

from mixonaut.utils.config import LOCK_FILE
from mixonaut.utils.logger import LoggerProtocol, ensure_logger, with_child_logger

TIMEOUT = 120  # secondes d'attente max


def is_process_alive(pid: int) -> bool:
    """
    Vérifie si un processus est en cours d'exécution.

    Args:
        pid (int): Identifiant du processus à vérifier.
    Returns:
        bool: True si le processus est en cours d'exécution, False sinon.
    """
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def read_lock_info() -> tuple[int | None, str | None]:
    """
    Lecture des informations de lock.

    Retourne un tuple contenant l'identifiant du processus et la timestamp de dernière vérification. Si les informations
    ne sont pas disponibles ou si une erreur se produit, retourne (None, None).
    """
    try:
        with open(LOCK_FILE) as f:
            lines = f.read().splitlines()
            pid = int(lines[0].split("=")[1])
            timestamp = lines[1].split("=")[1]
            return pid, timestamp
    except Exception:
        return None, None


def create_lock() -> bool:
    """
    Crée un lock en écrivant les informations de processus et timestamp dans le fichier LOCK_FILE.

    Si l'écriture réussit, retourne True. Sinon, retourne False.
    """
    try:
        with open(LOCK_FILE, "w") as f:
            f.write(f"PID={os.getpid()}\n")
            f.write(f"TIME={datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        return True
    except Exception as e:
        print(f"Erreur lors de la création du lock : {e}")
        return False


@with_child_logger
def wait_for_unlock(
    timeout: int = TIMEOUT, logger: LoggerProtocol | None = None
) -> bool:
    """
    Attend que le verrou soit libéré pour la base.

    Cette fonction attend jusqu'à atteindre un temps limite (défaut : 2 minutes) pour vérifier si le verrou est encore
    en cours d'utilisation. Si celui-ci n'est pas détecté, elle supprime automatiquement le fichier de verrou.
    """
    logger = ensure_logger(logger, __name__)
    waited = 0
    while os.path.exists(LOCK_FILE):
        pid, lock_time = read_lock_info()
        if pid and not is_process_alive(pid):
            logger.warning(
                "⚠️ Verrou orphelin détecté (PID %s à %s), suppression...",
                pid,
                lock_time,
            )
            os.remove(LOCK_FILE)
            break
        if waited >= timeout:
            logger.error(
                "❌ Base Beets toujours verrouillée après %d secondes. Abandon.",
                timeout,
            )
            return False
        logger.info(
            "🔒 Base en cours d'utilisation par PID %s (déposé à %s)... attente (%d/%d)",
            pid,
            lock_time,
            waited,
            timeout,
        )
        time.sleep(1)
        waited += 1
    return True


def get_current_pid() -> int:
    """
    Renvoie le PID actuel du processus.

    Retourne l'identifiant du processus qui est en cours d'exécution.
    """
    return os.getpid()


def read_lock_pid(
    lock_file: os.PathLike[str] | str = LOCK_FILE,
    logger: LoggerProtocol | None = None,
) -> int | None:
    """
    Lit un fichier de verrou et renvoie le PID s'il est présent sous forme 'PID=1234'.

    Retourne None si le fichier est absent, si le format n'est pas reconnu, ou si la valeur n'est pas un entier valide.
    """
    log = ensure_logger(logger, __name__)
    path = os.fspath(lock_file)

    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                m = re.match(r"\s*PID\s*=\s*(\d+)\s*$", line)
                if m:
                    return int(m.group(1))
        # Si on a lu tout le fichier sans trouver PID=...
        return None

    except FileNotFoundError:
        return None
    except OSError as exc:
        log.error("Erreur lecture lock file %s: %s", path, exc)
        return None


@with_child_logger
def safe_beets_call(logger: LoggerProtocol | None = None) -> bool:
    """
    Effectue une appel sécurisé à Beets après avoir vérifié que le verrou est libéré.

    Cette fonction attend jusqu'à atteindre un temps limite (défaut : 2 minutes) pour vérifier si le verrou est encore
    en cours d'utilisation. Si celui-ci n'est pas détecté, elle supprime automatiquement le fichier de verrou et
    effectue l'appel.
    """
    logger = ensure_logger(logger, __name__)
    if not wait_for_unlock(logger=logger):
        return False
    create_lock()
    return True
