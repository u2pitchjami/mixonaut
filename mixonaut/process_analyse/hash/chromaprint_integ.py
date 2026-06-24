# chromaprint_integ.py
"""
2020-08-20 module de traitemments des hashs.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from functools import partial
from typing import IO

from mixonaut.db.analyse.fingerprint_queries import mark_fp_error, upsert_fp_success
from mixonaut.utils.config import (
    FPCALC_MOUNT_CONTAINER,
    FPCALC_RUNNER,
    IMAGE_FPCALC,
    ESSENTIA_TEMP_AUDIO,
)
from mixonaut.utils.logger import LoggerProtocol, ensure_logger
from mixonaut.utils.utils_div import convert_path_format, to_container_path

# ────────────────────────────────────────────────────────────────────────────────
# Data model
# ────────────────────────────────────────────────────────────────────────────────


@dataclass
class FPResult:
    """
    Stores the result of a chromaprint fingerprint calculation.

    Attributes:
        fingerprint (str): The computed fingerprint.
        duration (int | None): The time it took to calculate the fingerprint in seconds. None if not available.
        chromaprint_version (int | None): The version of chromaprint used for calculation. None if not available.
    """

    fingerprint: str
    duration: int | None
    chromaprint_version: int | None = None


# ────────────────────────────────────────────────────────────────────────────────
# Low-level helpers
# ────────────────────────────────────────────────────────────────────────────────


def _sha1_file(path: str, block_size: int = 1024 * 1024) -> str | None:
    """
    SHA1 du contenu (inclut tags).
    """
    h = hashlib.sha1()
    host_path = convert_path_format(path=path)
    # st = os.stat(host_path)
    with open(host_path, "rb") as f:
        for chunk in iter(lambda: f.read(block_size), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_pcm(
    path: str,
    host_music_root: str = ESSENTIA_TEMP_AUDIO,
    ar: int = 11025,
    ac: int = 1,
    timeout_sec: int = 120,
    logger: LoggerProtocol | None = None,
) -> str | None:
    """
    Decode audio to raw PCM via ffmpeg and hash the stream (stable vs tags).
    """
    logger = ensure_logger(logger, __name__)
    cmd = [
        "docker",
        "run",
        "--rm",
        "-v",
        f"{str(host_music_root)}:{FPCALC_MOUNT_CONTAINER}:ro",
        IMAGE_FPCALC,
        "ffmpeg",
        "-nostdin",
        "-v",
        "error",
        "-i",
        str(path),
        "-map",
        "a:0",
        "-f",
        "s16le",
        "-ac",
        str(ac),
        "-ar",
        str(ar),
        "-",
    ]
    hasher = hashlib.sha256()
    logger.info("CMD = %r", cmd)
    try:
        with subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        ) as proc:
            stdout: IO[bytes] | None = proc.stdout
            if stdout is None:
                raise RuntimeError("Failed to open ffmpeg stdout pipe.")
            for chunk in iter(partial(stdout.read, 1024 * 1024), b""):
                if not chunk:
                    break
                hasher.update(chunk)
            _, stderr = proc.communicate(timeout=timeout_sec)
            if proc.returncode != 0:
                logger.error(
                    "ffmpeg failed for %s: %s",
                    path,
                    stderr.decode("utf-8", errors="ignore"),
                )
                raise RuntimeError("ffmpeg decode failed")
    except FileNotFoundError as exc:
        logger.error("ffmpeg not found. Please install ffmpeg.")
        raise exc
    return hasher.hexdigest()


def _parse_fpcalc_json(stdout: str) -> FPResult:
    s = stdout.strip()
    try:
        start = s.rfind("{")
        end = s.rfind("}")
        payload = s[start : end + 1] if start != -1 and end != -1 else s
        obj = json.loads(payload)
    except Exception as exc:
        raise ValueError(f"JSON fpcalc illisible: {exc}\nRAW={stdout[:300]}...")

    # duration
    dur = obj.get("duration")
    try:
        dur = int(round(float(dur))) if dur is not None else None
    except Exception:
        dur = None

    # fingerprint
    fp = obj.get("fingerprint") or obj.get("FINGERPRINT")
    if not fp:
        raise ValueError("fpcalc JSON: fingerprint manquant.")

    # version
    ver = obj.get("version") or obj.get("chromaprint_version")
    try:
        ver = int(ver) if ver is not None else None
    except Exception:
        ver = None

    return FPResult(fingerprint=fp, duration=dur, chromaprint_version=ver)


def _parse_fpcalc_text(stdout: str) -> FPResult:
    """
    Format texte classique:
      DURATION=123
      FINGERPRINT=1,2,3,...
    (certaines versions ajoutent VERSION= ou CHROMAPRINT_VERSION=)
    """
    dur = None
    fp = None
    ver = None
    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        up = line.upper()
        if up.startswith("DURATION="):
            try:
                dur = int(round(float(line.split("=", 1)[1].strip())))
            except Exception:
                dur = None
        elif up.startswith("FINGERPRINT="):
            fp = line.split("=", 1)[1].strip()
        elif up.startswith("VERSION=") or up.startswith("CHROMAPRINT_VERSION="):
            try:
                ver = int(line.split("=", 1)[1].strip())
            except Exception:
                ver = None
    if not fp:
        raise ValueError("fpcalc texte: FINGERPRINT manquant.")
    return FPResult(fingerprint=fp, duration=dur, chromaprint_version=ver)


def _parse_fpcalc_output(stdout: str) -> FPResult:
    s = stdout.strip()
    if s.startswith("{"):
        return _parse_fpcalc_json(s)
    return _parse_fpcalc_text(s)


def _to_container_path(host_path: str, host_music_root: str) -> str:
    """
    Mappe un chemin host vers le chemin conteneur selon le bind-mount.
    """
    if FPCALC_RUNNER != "docker":
        return host_path
    host_root = str(host_music_root).rstrip("/")
    cont_root = str(FPCALC_MOUNT_CONTAINER).rstrip("/")
    if host_path.startswith(host_root + "/"):
        return host_path.replace(host_root, cont_root, 1)
    # pas de mapping → on renvoie tel quel (au pire fpcalc échouera)
    return host_path


def _run_fpcalc(
    path: str,
    max_length: int | None = None,
    timeout: int = 60,
    prefer_json: bool = False,
    host_music_root: str = ESSENTIA_TEMP_AUDIO,
    logger: LoggerProtocol | None = None,
) -> FPResult:
    logger = ensure_logger(logger, __name__)
    target_path = path

    # Préfixe selon runner
    if FPCALC_RUNNER == "docker":
        prefix = [
            "docker",
            "run",
            "--rm",
            "-v",
            f"{str(host_music_root)}:{FPCALC_MOUNT_CONTAINER}:ro",
            IMAGE_FPCALC,
        ]

    else:
        # Mode local → s’assurer que fpcalc est dispo
        if shutil.which("fpcalc") is None:
            raise RuntimeError(
                "fpcalc introuvable sur le système. "
                "Installe-le (Debian/Ubuntu: 'sudo apt-get install libchromaprint-tools' · "
                "macOS: 'brew install chromaprint' · "
                "Arch: 'sudo pacman -S chromaprint' · "
                "Alpine: 'apk add chromaprint') "
                "ou utilise FPCALC_RUNNER='docker'."
            )
        prefix = []
        target_path = path
    base_cmd = prefix + ["fpcalc"]
    if max_length and max_length > 0:
        base_cmd += ["-length", str(int(max_length))]

    # 1) tentative JSON
    if prefer_json:
        cmd = base_cmd + ["-json", str(target_path)]

        cp = subprocess.run(
            cmd,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        logger.error("fpcalc JSON CMD: %r", cmd)
        logger.error("fpcalc JSON return code: %s", cp.returncode)
        # logger.error("fpcalc JSON stdout: %s", cp.stdout[-2000:])
        # logger.error("fpcalc JSON stderr: %s", cp.stderr[-2000:])

        if cp.returncode == 0 and cp.stdout.strip():
            return _parse_fpcalc_json(cp.stdout.strip())

        logger.warning(
            "fpcalc -json échoué, fallback texte. code=%s",
            cp.returncode,
        )
    # 2) fallback texte
    cmd = base_cmd + [
        str(target_path),
    ]
    p = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout,
    )

    logger.error("fpcalc return code: %s", p.returncode)
    # logger.error("fpcalc stdout: %s", p.stdout[-2000:])
    # logger.error("fpcalc stderr: %s", p.stderr[-2000:])

    if p.stderr:
        logger.debug("fpcalc stderr: %s", p.stderr.strip()[:400])

    # 👇 AJOUT ICI
    if p.returncode != 0:
        if p.stdout.strip():
            logger.warning(
                "fpcalc returned code=%s but produced usable output.",
                p.returncode,
            )
        else:
            raise RuntimeError(f"fpcalc échec code={p.returncode}: {p.stderr.strip()}")

    return _parse_fpcalc_output(p.stdout)


# ────────────────────────────────────────────────────────────────────────────────
# Public API
# ────────────────────────────────────────────────────────────────────────────────


def fingerprint_track(
    track_id: int,
    file_path: str,
    *,
    max_length: int | None = None,
    timeout: int = 60,
    prefer_json: bool = False,
    logger: LoggerProtocol | None = None,
) -> tuple[str, str | None]:
    """
    Calcule l’empreinte d’un fichier et écrit en base (fp_files + fp_links).

    Retourne (ok, message_d’erreur_éventuel).
    """
    logger = ensure_logger(logger, __name__)
    try:
        host_path = convert_path_format(path=file_path)
        container_path = to_container_path(host_path, "fpcalc")
        if not os.path.isfile(host_path):
            msg = f"Fichier introuvable: {host_path}"
            raise FileNotFoundError(msg)

        # SHA1 en premier (même si fpcalc échoue, on garde une trace par contenu)
        file_sha1 = _sha1_file(str(host_path))
        logger.debug("SHA1(%s) = %s", host_path, file_sha1)

        # SHA256
        file_sha256_pcm = sha256_pcm(path=str(container_path), logger=logger)
        logger.debug("SHA256_PCM(%s) = %s", container_path, file_sha256_pcm)

        # fpcalc
        fp = _run_fpcalc(
            str(container_path),
            max_length=max_length,
            timeout=timeout,
            prefer_json=prefer_json,
            logger=logger,
        )
        logger.debug("fp_calc = %s", fp)
        # upsert OK (écrit fp_files + fp_links)
        upsert_fp_success(
            track_id=track_id,
            file_sha1=file_sha1,
            file_sha256_pcm=file_sha256_pcm,
            fingerprint=fp.fingerprint,
            duration=fp.duration,
            chromaprint_version=fp.chromaprint_version,
            logger=logger,
        )
        return "OK", None

    except subprocess.CalledProcessError as e:
        msg = f"fpcalc échec (code={e.returncode})"
        try:
            file_sha1 = (
                _sha1_file(file_path) if os.path.exists(file_path) else "unknown"
            )
        except Exception:
            file_sha1 = "unknown"
        mark_fp_error(
            track_id=track_id, file_sha1=file_sha1, message=msg, logger=logger
        )
        return "KO", msg

    except subprocess.TimeoutExpired:
        msg = f"fpcalc timeout (> {timeout}s)"
        try:
            file_sha1 = (
                _sha1_file(file_path) if os.path.exists(file_path) else "unknown"
            )
        except Exception:
            file_sha1 = "unknown"
        mark_fp_error(
            track_id=track_id, file_sha1=file_sha1, message=msg, logger=logger
        )
        return "KO", msg

    except Exception as e:
        msg = f"Erreur: {e}"
        try:
            file_sha1 = (
                _sha1_file(file_path) if os.path.exists(file_path) else "unknown"
            )
        except Exception:
            file_sha1 = "unknown"
        mark_fp_error(
            track_id=track_id, file_sha1=file_sha1, message=msg, logger=logger
        )
        return "KO", msg


# def lookup_and_update_acoustid(track_id: str,
#                                acoustid_id: str,
#                                confidence: Optional[float],
#                                logger=None) -> None:
#     """
#     Si tu ajoutes plus tard un lookup AcoustID en ligne,
#     appelle cette fonction pour marquer la correspondance côté fp_files.
#     """
#     update_acoustid(file_sha1=file_sha1, acoustid_id=acoustid_id, confidence=confidence, logger=logger)

# def _abspath(host_music_root: Path, db_path: str) -> Path:
#     """Résout le chemin Beets (relatif ou absolu) en chemin absolu côté host."""
#     if not db_path:
#         return host_music_root
#     # beets peut enregistrer des bytes → str
#     if isinstance(db_path, (bytes, bytearray)):
#         db_path = db_path.decode(errors="ignore")
#     p = Path(db_path)
#     return p if p.is_absolute() else (host_music_root / p)
