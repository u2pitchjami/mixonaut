import re
from pathlib import Path
from datetime import datetime
from utils.config import BEETS_MUSIC, HOST_MUSIC, WINDOWS_MUSIC
from utils.logger import get_logger, with_child_logger

@with_child_logger
def format_percent(part: int, total: int, digits: int = 0, logger: str = None) -> str:
    """
    Calcule un pourcentage (part/total) en gérant la division par zéro.
    Retourne une chaîne formatée avec '%' (arrondi à `digits` décimales).
    """
    try:
        if total == 0:
            return "N/A"
        percent = (part / total) * 100
        return f"{percent:.{digits}f}%"
    except Exception as e:
        logger.warning(f"Erreur de calcul pourcentage : {e}")
        return "ERR%"

@with_child_logger
def format_nb(nb: int, insécable: bool = False, logger: str = None) -> str:
    """
    Formate un entier avec des séparateurs de milliers.
    Par défaut : espace normal. Si insécable=True, utilise l'espace fine insécable (U+202F).
    """
    try:
        return f"{nb:,}".replace(",", " " if insécable else " ")
    except Exception as e:
        logger.warning(f"Erreur de formatage du nombre : {e}")
        return str(nb)

def ensure_to_str(path) -> str:
    """
    Convertit un path potentiellement en bytes ou Path en str propre.
    """
    if isinstance(path, bytes):
        path = path.decode("utf-8")
    return str(Path(path))

def ensure_to_path(path):
    """
    Garantit qu'un chemin est une chaîne ou un Path valide.
    Convertit les objets bytes → str, et renvoie un Path.
    """
    if isinstance(path, bytes):
        path = path.decode('utf-8')  # ou 'latin-1' selon ton encodage Beets
    return Path(path)

def convert_path_format(path: Path, to_beets: bool = False) -> Path:
    """
    Convertit un chemin entre formats :
    - beets ↔ normal
    - windows ↔ beets ou normal

    :param path: chemin en Path (beets, normal ou windows)
    :param to_beets: si True, convertit vers format beets
    :return: Path converti
    """
    # Sécurité pour s'assurer que c'est bien un Path
    if not isinstance(path, Path):
        path = Path(path)

    if to_beets:
        if str(path).startswith(str(HOST_MUSIC)):
            relative = path.relative_to(HOST_MUSIC)
            return Path(BEETS_MUSIC) / relative
        elif str(path).startswith("W:\\") or str(path).startswith("W:/"):
            # Conversion chemin Windows vers chemin Beets
            windows_relative = Path(str(path).replace("W:\\Collection\\", "").replace("\\", "/"))
            return Path(BEETS_MUSIC) / windows_relative
    else:
        if str(path).startswith(str(BEETS_MUSIC)):
            relative = path.relative_to(BEETS_MUSIC)
            return Path(HOST_MUSIC) / relative

    raise ValueError(f"Chemin non reconnu ou non convertible : {path}")

def get_current_timestamp():
    """Retourne l’horodatage actuel au format ISO 8601 (secondes)"""
    return datetime.now().isoformat(timespec="seconds")

def add_updated_at(field_values: dict) -> dict:
    """
    Ajoute la clé 'updated_at' avec la date courante dans le dictionnaire field_values.
    """
    field_values["updated_at"] = get_current_timestamp()
    return field_values

@with_child_logger
def sanitize_value(value, format_type: str, logger: str = None):
    if value is None:
        return None
    try:
        if format_type == "bpm":
            bpm = int(round(float(value)))
            if 40 <= bpm <= 300:
                return bpm
            logger.warning(f"❌ BPM hors limites : {bpm}")
            return None

        elif format_type == "rg_gain":
            return round(float(value), 2)

        elif format_type == "key":
            val = str(value).strip().lower()
            if re.match(r"^\d{1,2}[ab]$", val):
                return val
            logger.warning(f"❌ Key non conforme : {val}")
            return None

        elif format_type == "mood":
            return str(value).strip().lower()

        # Ajoute ici d’autres formats si besoin
        else:
            logger.warning(f"❓ Format non reconnu : {format_type}")
            return value

    except Exception as e:
        logger.warning(f"❌ Erreur sur {format_type} : {value} ({e})")
        return None
