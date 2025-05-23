import os
from datetime import datetime
from utils.logger import get_logger

def extract_paths_from_file(source_file: str, output_file: str, mode: str = "path_extract", logname = None) -> None:
    """
    Extrait des chemins à partir d'un fichier en fonction du mode :
    - mode 'skip' : lignes commençant par 'skip '
    - mode 'path_extract' : cherche des chemins contenant '/app/data/'
    """
    logger = get_logger(logname + "." + __name__)
    if not os.path.isfile(source_file):
        logger.warning(f"Fichier introuvable : {source_file}")
        return

    try:
        with open(source_file, "r", encoding="utf-8") as f:
            lines = f.readlines()

        if mode == "skip":
            extracted = [line[5:].strip() for line in lines if line.startswith("skip ")]
        elif mode == "path_extract":
            extracted = []
            for line in lines:
                index = line.find("/app/data/")
                if index != -1:
                    extracted.append(line[index:].strip())
        else:
            logger.error(f"Mode inconnu : {mode}")
            return

        if extracted:
            with open(output_file, "a", encoding="utf-8") as f_out:
                for entry in extracted:
                    f_out.write(entry + "\n")

            logger.info(f"[{datetime.now()}] - {len(extracted)} entrées extraites en mode '{mode}'")
        else:
            logger.info("Aucune entrée trouvée à extraire.")

        # Nettoyage et dédoublonnage
        with open(output_file, "r", encoding="utf-8") as f:
            unique_lines = sorted(set(line.strip() for line in f if line.strip()))

        with open(output_file, "w", encoding="utf-8") as f:
            for line in unique_lines:
                f.write(line + "\n")

        logger.info(f"Fichier récap dispo dans : {output_file}")

        if mode == "skip":
            # Vider le fichier d'origine seulement pour le mode log (éviter perte si fichier manuel)
            open(source_file, "w", encoding="utf-8").close()

    except Exception as e:
        logger.error(f"Erreur durant l'extraction ({mode}) : {e}")
