"""
2025-08-20.

modules de préparation des fichiers pour essentia.
"""

import re
import shutil
import unicodedata
from pathlib import Path

from mixonaut.utils.config import (
    ESSENTIA_SAV_JSON,
    ESSENTIA_TEMP_AUDIO,
    ESSENTIA_TEMP_JSON,
    MAX_SAFENAME_LENGTH,
)
from mixonaut.utils.logger import LoggerProtocol, ensure_logger
from mixonaut.utils.utils_div import convert_path_format, ensure_to_path


def generate_mode_text(
    count: int | None = None,
    missing_features: bool = False,
    is_edm: bool = False,
    missing_field: str | None = None,
    path_contains: str | None = None,
) -> str:
    """
    Générer un texte explicite du mode actif.

    Args:
        count (int): Nombre de morceaux à traiter.
        missing_features (bool): Si le traitement manque des features audio.
        is_edm (bool): Si la traitement est exclusive pour les EDM.
        missing_field (str): Champ manquant dans le fichier.
        path_contains (str): Path contenant un élément spécifique.

    Returns:
        str: Texte explicite du mode actif.
    """
    # Générer le texte de mode
    mode_label = []
    if count:
        mode_label.append(f"Traitement de {count} morceaux")
    else:
        mode_label.append("Traitement de tous les morceaux")

    if missing_features:
        mode_label.append("absents de audio_features")
    if is_edm:
        mode_label.append("EDM uniquement")
    if missing_field:
        mode_label.append(f"champ manquant : {missing_field}")
    if path_contains:
        mode_label.append(f"path contient « {path_contains} »")

    # Revenir à la phrase de terminaison
    mode_text = " | ".join(mode_label) if mode_label else "Tous les morceaux"
    return mode_text


def prep_track(
    track: tuple[int, str, str, str, str, str, str, str, str, float | None],
    logger: LoggerProtocol | None = None,
) -> tuple[int, Path, str, Path, Path, Path]:
    """
    Prépare les chemins pour l'analyse d'un morceau.
    Args:
        track: Chemin du morceau à analyser.
        logger: Objectif pour loguer les messages.

    Returns:
        tuple[int, Path, str, Path, Path, Path]: Les chemins préparés pour l'analyse.
    """
    logger = ensure_logger(logger, __name__)
    try:
        result = prepare_track_paths(track, logger=logger)
        if result is None:
            logger.error(f"❌ Erreur préparation des chemins pour le morceau : {track}")
            msg = f"Fichier introuvable: {track[1]}"
            raise FileNotFoundError(msg)
        track_id, original_path, safe_name, temp_audio, temp_json, temp_json_madmom = (
            result
        )
        if not process_audio_file(original_path, temp_audio, logger=logger):
            raise FileNotFoundError(msg)
        return (
            track_id,
            original_path,
            safe_name,
            temp_audio,
            temp_json,
            temp_json_madmom,
        )
    except Exception as e:
        logger.exception(f"❌ Erreur traitement track {track_id} : {e}")
        raise FileNotFoundError(msg)


def prepare_track_paths(
    track: tuple[int, str, str, str, str, str, str, str, str, float | None],
    logger: LoggerProtocol | None = None,
) -> tuple[int, Path, str, Path, Path, Path] | None:
    """
    Prepare track paths for Essentia processing.

    This function takes a track (a tuple containing the track ID, raw path,
    artist, album, and title) and prepares the necessary file paths for
    Essentia processing. If the file exists at the specified raw path, it is
    replaced with a temporary path to avoid overwriting existing files.
    Args:
        track: A tuple containing the track ID, raw path, artist, album, and title.
        logger: An optional LoggerProtocol instance for logging purposes.

    Returns:
        A tuple containing the track ID, prepared path, safe name, temp audio
        file path, and temp JSON file path. If an error occurs during processing,
        the function raises an exception with a descriptive error message.
    """
    logger = ensure_logger(logger, __name__)
    try:
        track_id, raw_path, artist, album, title, _, _, _, _, duration = track
        path = Path(convert_path_format(ensure_to_path(raw_path), to_beets=False))
        if not path.exists():
            logger.warning(f"Fichier introuvable : {path}")
            return None

        safe_name = f"{track_id}_{sanitize_filename(artist)}_{sanitize_filename(album)}_{sanitize_filename(title)}"
        safe_name_madmom = f"{track_id}_mm-{sanitize_filename(artist)}_{sanitize_filename(album)}_{sanitize_filename(title)}"
        # Tronque si trop long
        if len(safe_name) > MAX_SAFENAME_LENGTH:
            safe_name = safe_name[:MAX_SAFENAME_LENGTH]
        temp_audio = Path(ESSENTIA_TEMP_AUDIO) / f"{safe_name}{path.suffix}"
        temp_json = Path(ESSENTIA_TEMP_JSON) / f"{safe_name}.json"
        temp_json_madmom = Path(ESSENTIA_TEMP_JSON) / f"{safe_name_madmom}.json"
        return (track_id, path, safe_name, temp_audio, temp_json, temp_json_madmom)
    except Exception as e:
        logger.error(f"Erreur préparation chemins : {e}")
        raise


def process_audio_file(
    original_path: Path, temp_audio: Path, logger: LoggerProtocol | None = None
) -> bool:
    """
    Process the audio file and copy it to the temporary location.
    Args:
        original_path (str): The path to the original audio file.
        temp_audio (Path): The temporary directory where the audio will be copied.
        logger (LoggerProtocol, optional): The logger instance. Defaults to None.

    Returns:
        bool: True if the copy operation was successful, False otherwise.
    """
    logger = ensure_logger(logger, __name__)
    try:
        shutil.copy(original_path, temp_audio)
        return True
    except Exception as e:
        logger.error(f"Erreur copie fichier audio : {e}")
        return False


def sanitize_filename(name: str) -> str:
    """
    Sanitize a filename by removing accents and non-alphanumeric characters.

    Args:
        name (str): The filename to be sanitized.

    Returns:
        str: The sanitized filename.
    """
    # Enlève les accents
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    # Garde uniquement lettres, chiffres, tirets, underscores
    name = re.sub(r"[^\w\-]", "_", name)
    # Remplace multiples underscores par un seul
    name = re.sub(r"__+", "_", name)
    return name.strip("_").lower()


def clean_temp_files(
    *paths: Path | None,
    logger: LoggerProtocol | None = None,
) -> None:
    """
    Supprime les fichiers temporaires générés pendant la préparation.
    """
    logger = ensure_logger(logger, __name__)

    for path in paths:
        if path is None:
            continue

        try:
            if path.exists():
                path.unlink()

        except Exception as exc:
            logger.warning(
                "Erreur suppression fichier temporaire : %s -> %s",
                path,
                exc,
            )


def archive_json_result(
    track_id: int, safe_name: str, logger: LoggerProtocol | None = None
) -> None:
    """
    Déplace un JSON de `temp_folder` vers `archive_base/XXXX/` en fonction de track_id.
    """
    logger = ensure_logger(logger, __name__)
    # Dossier de destination
    target_folder = Path(ESSENTIA_SAV_JSON) / f"{(track_id // 1000) * 1000:04d}"
    target_folder.mkdir(parents=True, exist_ok=True)

    # Fichier source et destination
    source = Path(ESSENTIA_TEMP_JSON) / f"{safe_name}.json"
    dest = target_folder / f"{safe_name}.json"

    if not source.exists():
        logger.warning(
            f"❌ JSON temporaire non trouvé pour track {track_id} : {source}"
        )
        return
    try:
        shutil.copy(source, dest)
        logger.debug(f"✅ JSON archivé : {dest}")
    except Exception as e:
        logger.warning(f"Erreur archivage JSON {track_id} : {e}")
