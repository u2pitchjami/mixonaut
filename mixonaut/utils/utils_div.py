"""2025-08-20 - fonctions diverses."""

import re
from pathlib import Path

from mixonaut.utils.config import BEETS_MUSIC, HOST_MUSIC, WINDOWS_MUSIC
from mixonaut.utils.logger import LoggerProtocol, ensure_logger, with_child_logger


@with_child_logger
def format_percent(
    part: int, total: int, digits: int = 0, logger: LoggerProtocol | None = None
) -> str:
    """
    Calcule un pourcentage (part/total) en gérant la division par zéro.

    Retourne une chaîne formatée avec '%' (arrondi à `digits` décimales).
    """
    logger = ensure_logger(logger, __name__)
    try:
        if total == 0:
            return "N/A"
        percent = (part / total) * 100
        return f"{percent:.{digits}f}%"
    except Exception as e:
        logger.warning(f"Erreur de calcul pourcentage : {e}")
        return "ERR%"


@with_child_logger
def format_nb(
    nb: int, insécable: bool = False, logger: LoggerProtocol | None = None
) -> str:
    """
    Formate un entier avec des séparateurs de milliers.

    Par défaut : espace normal. Si insécable=True, utilise l'espace fine insécable (U+202F).
    """
    logger = ensure_logger(logger, __name__)
    try:
        return f"{nb:,}".replace(",", " " if insécable else " ")
    except Exception as e:
        logger.warning(f"Erreur de formatage du nombre : {e}")
        return str(nb)


def ensure_to_str(path: Path | bytes) -> str:
    """
    Convertit un path potentiellement en bytes ou Path en str propre.
    """
    if isinstance(path, bytes):
        path_bytes = path.decode("utf-8")
        return str(path_bytes)
    return str(path)


def ensure_to_path(path: str | bytes) -> Path:
    """
    Garantit qu'un chemin est une chaîne ou un Path valide.

    Convertit les objets bytes → str, et renvoie un Path.
    """
    if isinstance(path, bytes):
        path_bytes = path.decode("utf-8")
        return Path(path_bytes)
    return Path(path)


def convert_path_format(path: Path | str, to_beets: bool = False) -> Path:
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
        elif str(path).startswith(WINDOWS_MUSIC) or str(path).startswith("W:/"):
            # Conversion chemin Windows vers chemin Beets
            windows_relative = Path(
                str(path).replace(WINDOWS_MUSIC, "").replace("\\", "/")
            )
            return Path(BEETS_MUSIC) / windows_relative
    else:
        if str(path).startswith(str(BEETS_MUSIC)):
            relative = path.relative_to(BEETS_MUSIC)
            return Path(HOST_MUSIC) / relative

    raise ValueError(f"Chemin non reconnu ou non convertible : {path}")


def map_to_navidrome_path(
    source_path: str,
    source_root: Path,
    navidrome_root: Path,
    logger: LoggerProtocol | None = None,
) -> str:
    """
    Map an internal audio path to a Navidrome-compatible path.

    Example:
    /app/data/Artist/Album/track.flac
    → /music/Artist/Album/track.flac
    """
    logger = ensure_logger(logger, __name__)

    try:
        source = Path(source_path).resolve()
        relative = source.relative_to(source_root)
        mapped = navidrome_root / relative

        return str(mapped)

    except ValueError as exc:
        logger.error(
            "Path mapping failed: %s is not under %s",
            source_path,
            source_root,
        )
        raise RuntimeError("Invalid source path for Navidrome mapping") from exc


# def get_current_timestamp():
#     """Retourne l’horodatage actuel au format ISO 8601 (secondes)"""
#     return datetime.now().isoformat(timespec="seconds")

# def add_updated_at(field_values: dict) -> dict:
#     """
#     Ajoute la clé 'updated_at' avec la date courante dans le dictionnaire field_values.
#     """
#     field_values["updated_at"] = get_current_timestamp()
#     return field_values


@with_child_logger
def sanitize_value(
    value: int | float | str | None,
    format_type: str,
    logger: LoggerProtocol | None = None,
) -> None | int | float | str:
    """
    Sanitise une valeur d'entrée en fonction de son type.

    Retourne la valeur sanitiée s'il est possible ; sinon retourne None.
    """
    logger = ensure_logger(logger, __name__)
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


# @with_child_logger
# def clear_folder(folder_path, logger=None):
#     logger.info(f"Vidage du contenu du dossier temporaire : {folder_path}")
#     for filename in os.listdir(folder_path):
#         file_path = os.path.join(folder_path, filename)
#         try:
#             if os.path.isfile(file_path) or os.path.islink(file_path):
#                 os.unlink(file_path)
#                 logger.debug(f"Fichier supprimé : {file_path}")
#             elif os.path.isdir(file_path):
#                 shutil.rmtree(file_path)
#                 logger.debug(f"Dossier supprimé : {file_path}")
#         except Exception as e:
#             logger.error(f"Erreur lors de la suppression de {file_path} : {e}")
