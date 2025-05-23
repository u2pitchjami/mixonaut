import os
import time

def rotate_logs(log_dir, keep_days=30, logf=None):
    """
    Supprime les fichiers de log dans log_dir plus vieux que keep_days.
    Écrit les actions dans un fichier de log si logf est fourni.
    """
    now = time.time()
    cutoff = now - (keep_days * 86400)

    def log(message):
        print(message)
        if logf:
            logf.write(f"{message}\n")

    if not os.path.isdir(log_dir):
        log(f"[LOG ROTATION] Dossier de logs introuvable : {log_dir}")
        return

    for filename in os.listdir(log_dir):
        filepath = os.path.join(log_dir, filename)
        if os.path.isfile(filepath):
            if os.path.getmtime(filepath) < cutoff:
                try:
                    os.remove(filepath)
                    log(f"[LOG ROTATION] Supprimé : {filepath}")
                except Exception as e:
                    log(f"[LOG ROTATION] Erreur suppression {filepath} : {e}")
