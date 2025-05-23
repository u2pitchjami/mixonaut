from pathlib import Path
from datetime import datetime
from utils.config import BEETS_MUSIC, HOST_MUSIC, WINDOWS_MUSIC
from utils.logger import get_logger

def ensure_to_str(path) -> str:
    """
    Convertit un path potentiellement en bytes ou Path en str propre.
    """
    if isinstance(path_like, bytes):
        path_like = path_like.decode("utf-8")
    return str(Path(path_like))

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
