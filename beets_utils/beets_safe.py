import os
import subprocess
import sys
import time
from utils.logger import get_logger
from datetime import datetime
from utils.config import LOCK_FILE

logname = "beets_safe"
TIMEOUT = 30  # secondes d'attente max

def is_process_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False

def read_lock_info():
    try:
        with open(LOCK_FILE, 'r') as f:
            lines = f.read().splitlines()
            pid = int(lines[0].split("=")[1])
            timestamp = lines[1].split("=")[1]
            return pid, timestamp
    except Exception:
        return None, None

def create_lock():
    with open(LOCK_FILE, 'w') as f:
        f.write(f"PID={os.getpid()}\n")
        f.write(f"TIME={datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

def wait_for_unlock(timeout=TIMEOUT, logname=logname):
    logger = get_logger(logname)
    waited = 0
    while os.path.exists(LOCK_FILE):
        pid, lock_time = read_lock_info()
        if pid and not is_process_alive(pid):
            logger.warning("⚠️ Verrou orphelin détecté (PID %s à %s), suppression...", pid, lock_time)
            os.remove(LOCK_FILE)
            break
        if waited >= timeout:
            logger.error("❌ Base Beets toujours verrouillée après %d secondes. Abandon.", timeout)
            return False
        logger.info("🔒 Base en cours d'utilisation par PID %s (déposé à %s)... attente (%d/%d)", pid, lock_time, waited, timeout)
        time.sleep(1)
        waited += 1
    return True

def get_current_pid():
    return os.getpid()

def read_lock_pid():
    try:
        with open(LOCK_FILE, 'r') as f:
            for line in f:
                if line.startswith("PID="):
                    return int(line.strip().split("=")[1])
    except Exception:
        return None

def safe_beets_call(logname=logname) -> int:
    logger = get_logger(logname)
    if not wait_for_unlock():
        return False

    create_lock()
    return True
