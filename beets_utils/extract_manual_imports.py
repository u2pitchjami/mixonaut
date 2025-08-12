import os
from utils.config import BEETS_LOGS, BEETS_MANUAL_LIST
from utils.logger import with_child_logger

def parse_beets_log(lines):
    """
    Trie les lignes du log Beets et retourne trois listes : skips, doublons, imports réussis.
    """
    skipped = []
    duplicates = []
    moved = []
    for line in lines:
        if line.startswith("skip "):
            skipped.append(line[5:].strip())
        elif line.startswith("duplicate-skip "):
            duplicates.append(line[15:].strip())        
        elif line.startswith("[MOVED]|||"):
            parts = line.strip().split("|||")
            if len(parts) == 5:
                source_path = parts[3].strip()
                moved.append(source_path)
    print(f"Moved: {moved}")
    return skipped, duplicates, moved


@with_child_logger
def extract_manual_imports(logger=None):
    """
    Analyse le log Beets et extrait les albums à traiter manuellement.
    Écrit les chemins marqués [skip] ou [duplicate] dans le fichier manuel.
    """
    if not os.path.isfile(BEETS_LOGS):
        logger.warning(f"Fichier log introuvable : {BEETS_LOGS}")
        return

    try:
        with open(BEETS_LOGS, "r", encoding="utf-8") as f:
            lines = f.readlines()

        skipped, duplicates, moved = parse_beets_log(lines)

        total = skipped + duplicates
        if total:
            logger.info(f"{len(skipped)} albums ignorés, {len(duplicates)} doublons.")
            with open(BEETS_MANUAL_LIST, "a", encoding="utf-8") as f_out:
                for entry in skipped:
                    f_out.write(f"[skip] {entry}\n")
                    logger.info(f"[skip] {entry}\n")
                for entry in duplicates:
                    f_out.write(f"[duplicate] {entry}\n")
                    logger.info(f"[duplicate] {entry}\n")
        else:
            logger.info("Aucun album à importer manuellement trouvé.")

        # Nettoyage : tri, unicité
        with open(BEETS_MANUAL_LIST, "r", encoding="utf-8") as f:
            unique_lines = sorted(set(line.strip() for line in f if line.strip()))

        with open(BEETS_MANUAL_LIST, "w", encoding="utf-8") as f:
            for line in unique_lines:
                f.write(line + "\n")

        # Vider le fichier de log
        open(BEETS_LOGS, "w", encoding="utf-8").close()
        
        logger.info(f"Fichier récap dispo dans : {BEETS_MANUAL_LIST}")
        if moved:
            logger.info(f"{len(moved)} albums importés avec succès.")
            return moved
                
        

    except Exception as e:
        logger.error(f"Erreur durant l'extraction : {e}")