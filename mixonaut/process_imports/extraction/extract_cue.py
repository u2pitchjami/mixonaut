"""
2020-08-20 module spécifique cue.
"""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from mixonaut.utils.logger import LoggerProtocol, ensure_logger, with_child_logger


@with_child_logger
def get_audio_base_name(cue_path: str, logger: LoggerProtocol | None = None) -> str:
    """
    Extracts the audio base name from a .cue file path.

    The function removes any recursive extensions (e.g. .cue, .flac.cue, .wav.cue, etc.)

    Args:
        cue_path (str): Path to the .cue file.
        logger (LoggerProtocol | None, optional): Logger instance. Defaults to None.

    Returns:
        str: The audio base name without extensions.
    """
    logger = ensure_logger(logger, __name__)
    base = os.path.basename(cue_path)
    logger.debug(f"Base name before processing: {base}")
    # Supprime récursivement les extensions .cue, .flac.cue, .wav.cue, etc.
    while base.lower().endswith(".cue"):
        base = os.path.splitext(base)[0]
        base = sanitize_cue_filename(base)
    logger.debug(f"Base name after processing: {base}")
    return base


# @with_child_logger
# def convert_wav_to_flac(wav_path, flac_path, logger=None):
#     cmd = ["ffmpeg", "-i", wav_path, "-compression_level", "12", flac_path]
#     logger.debug(f"Conversion WAV → FLAC : {' '.join(cmd)}")
#     subprocess.run(cmd, check=True)

# @with_child_logger
# def convert_wav_to_mp3(wav_path, mp3_path, logger=None):
#     cmd = ["ffmpeg", "-i", wav_path, "-q:a", "2", mp3_path]
#     logger.debug(f"Conversion WAV → MP3 : {' '.join(cmd)}")
#     subprocess.run(cmd, check=True)


def sanitize_cue_filename(name: str) -> str:
    """
    Supprime les guillemets, les espaces en début/fin et les doublons internes.
    """
    cleaned = name.strip().strip('"').replace("  ", " ")
    return cleaned.strip()


@with_child_logger
def split_cue_and_convert_ffmpeg(cue_path, logger: LoggerProtocol | None = None):
    """
    Découpe un fichier audio avec un fichier CUE via ffmpeg, compatible FLAC/MP3/WAV/APE.

    Retourne un dossier temporaire contenant les pistes.
    """
    logger = ensure_logger(logger, __name__)
    try:
        cue_dir = os.path.dirname(cue_path)
        cue_base = get_audio_base_name(cue_path, logger=logger)

        audio_file = None
        for ext in [".flac", ".mp3", ".wav", ".ape", ".wv", ""]:
            candidate = os.path.join(cue_dir, cue_base + ext)
            if os.path.exists(candidate):
                audio_file = candidate
                if logger:
                    logger.debug(f"Fichier audio trouvé : {audio_file}")
                break

        if not audio_file:
            if logger:
                logger.error(f"Fichier audio associé au cue non trouvé pour {cue_path}")
            return None

        # 1. Récupérer les points de split
        cue_cmd = ["cuebreakpoints", cue_path]
        result = subprocess.run(cue_cmd, capture_output=True, text=True, check=True)
        lines = result.stdout.strip().splitlines()
        points = ["00:00:00"] + lines + ["99:59:59"]

        # 2. Découpe via ffmpeg
        with tempfile.TemporaryDirectory(prefix="cue_split_ffmpeg_") as temp_out:
            out_dir = Path(temp_out)

            ext = Path(audio_file).suffix.lower().replace(".", "")
            if ext not in ["flac", "mp3", "wav"]:
                ext = "flac"  # fallback
            codec = {"flac": "flac", "mp3": "libmp3lame", "wav": "pcm_s16le"}.get(
                ext, "flac"
            )

            for idx, (start, end) in enumerate(zip(points[:-1], points[1:]), 1):
                track_num = f"{idx:02}"
                out_file = out_dir / f"track{track_num}.{ext}"
                cmd = [
                    "ffmpeg",
                    "-i",
                    audio_file,
                    "-ss",
                    start,
                    "-to",
                    end,
                    "-c:a",
                    codec,
                    "-map_metadata",
                    "-1",
                    "-loglevel",
                    "error",
                    str(out_file),
                ]
                if logger:
                    logger.debug(
                        f"[FFMPEG] Découpe {track_num}: {start} → {end} en .{ext}"
                    )
                subprocess.run(cmd, check=True)

            # Copie vers un dossier temporaire persistant
            final_dir = tempfile.mkdtemp(prefix="cue_final_ffmpeg_")
            for f in out_dir.iterdir():
                shutil.copy2(f, final_dir)

            if logger:
                logger.info(f"Split terminé. Fichiers générés dans : {final_dir}")
            return final_dir

    except subprocess.CalledProcessError as e:
        if logger:
            logger.error(f"Erreur subprocess : {e}")
        return None
    except Exception as e:
        if logger:
            logger.error(f"Erreur inattendue dans split_cue_and_convert_ffmpeg : {e}")
        return None
