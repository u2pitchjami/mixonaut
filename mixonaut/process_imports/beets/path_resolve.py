"""
2020-08-20 module de gestion des chemins entre le host et le conteneur.
"""

# process_imports/path_resolve.py
from __future__ import annotations

import os
from pathlib import Path, PurePosixPath

from mixonaut.utils.config import BEETS_IMPORT_PATH, MUSIC_IMPORT_PATH
from mixonaut.utils.logger import LoggerProtocol, ensure_logger
from mixonaut.utils.utils_div import convert_path_format


def _safe_relative_to(p: Path, base: Path) -> str | None:
    try:
        return str(p.resolve().relative_to(base.resolve()))
    except Exception:
        return None


def _beets_to_host_via_prefix(p: Path) -> Path:
    """
    Remplace juste le préfixe /app/imports → /mnt/.../imports (rapide).
    """
    beets_base = Path(BEETS_IMPORT_PATH).as_posix().rstrip("/")
    s = p.as_posix().strip()
    if s.startswith(beets_base):
        suffix = s[len(beets_base) :].lstrip("/")
        return Path(MUSIC_IMPORT_PATH) / suffix
    return p


def _beets_to_host_via_converter(p: Path) -> Path:
    """
    Essaye avec ta utilité convert_path_format (gère Windows, etc.).
    """
    try:
        return convert_path_format(p, to_beets=False)  # vers host
    except Exception:
        return p  # on retombe sur p si non convertible


def resolve_album_path_and_rel(
    path_str: str, logger: LoggerProtocol | None = None
) -> tuple[Path, str] | None:
    """
    Accepte un chemin Beets (conteneur) ou host et renvoie (host_path, rel_dir_sous_imports).

    Renvoie None si le chemin ne pointe pas vers /imports/ (host ou conteneur).
    """
    logger = ensure_logger(logger, __name__)
    raw = Path(path_str)
    logger.debug(f"raw={raw}")

    def _norm_rel(s: str) -> str:
        return os.path.normpath(s).replace("\\", "/").lstrip("./")

    # 1) Si déjà sous MUSIC_IMPORT_PATH → parfait
    base = Path(MUSIC_IMPORT_PATH).resolve()
    logger.debug(f"base={base}")

    try:
        rel = raw.resolve().relative_to(base).as_posix()
        logger.debug(f"rel={rel}")
        return raw, _norm_rel(rel)
    except Exception:
        pass

    # 2) Chemin Beets (/app/imports/...)
    if BEETS_IMPORT_PATH and raw.as_posix().startswith(
        Path(BEETS_IMPORT_PATH).as_posix().rstrip("/")
    ):
        host_guess = _beets_to_host_via_prefix(raw)
        logger.debug(f"host_guess={host_guess}")
        try:
            rel = host_guess.resolve().relative_to(base).as_posix()
            logger.debug(f"rel2={rel}")
            return host_guess, _norm_rel(rel)
        except Exception:
            host_conv = _beets_to_host_via_converter(raw)
            logger.debug(f"host_conv={host_conv}")
            try:
                rel = host_conv.resolve().relative_to(base).as_posix()
                logger.debug(f"rel3={rel}")
                return host_conv, _norm_rel(rel)
            except Exception:
                pass

    # 3) Fallback “ancre /imports/”
    parts = PurePosixPath(raw.as_posix()).parts
    logger.debug(f"parts={parts}")
    if "imports" in parts:
        idx = parts.index("imports")
        suffix = "/".join(parts[idx + 1 :])  # Artist/Album[/CD1]
        suffix = _norm_rel(suffix)
        rebuilt = (base / suffix).resolve()
        return rebuilt, suffix

    return None
