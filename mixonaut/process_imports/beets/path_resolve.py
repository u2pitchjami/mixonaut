# process_imports/path_resolve.py
from __future__ import annotations
from pathlib import Path, PurePosixPath
from typing import Optional, Tuple
from utils.config import BEETS_IMPORT_PATH, MUSIC_IMPORT_PATH
from utils.utils_div import convert_path_format  # ta fonction existante

def _safe_relative_to(p: Path, base: Path) -> Optional[str]:
    try:
        return str(p.resolve().relative_to(base.resolve()))
    except Exception:
        return None

def _beets_to_host_via_prefix(p: Path) -> Path:
    """Remplace juste le préfixe /app/imports → /mnt/.../imports (rapide)."""
    beets_base = Path(BEETS_IMPORT_PATH).as_posix().rstrip("/")
    s = p.as_posix().strip()
    if s.startswith(beets_base):
        suffix = s[len(beets_base):].lstrip("/")
        return Path(MUSIC_IMPORT_PATH) / suffix
    return p

def _beets_to_host_via_converter(p: Path) -> Path:
    """Essaye avec ta utilité convert_path_format (gère Windows, etc.)."""
    try:
        return convert_path_format(p, to_beets=False)  # vers host
    except Exception:
        return p  # on retombe sur p si non convertible

def resolve_album_path_and_rel(path_str: str) -> Optional[Tuple[Path, str]]:
    """
    Accepte un chemin Beets (conteneur) ou host et renvoie (host_path, rel_dir_sous_imports).
    Renvoie None si le chemin ne pointe pas vers /imports/ (host ou conteneur).
    """
    raw = Path(path_str)

    # 1) Si c'est déjà sous MUSIC_IMPORT_PATH → parfait
    rel = _safe_relative_to(raw, Path(MUSIC_IMPORT_PATH))
    if rel is not None:
        return raw, rel

    # 2) Si ça ressemble à un chemin Beets (/app/imports/...), tente prefix + convert_path_format
    if BEETS_IMPORT_PATH and raw.as_posix().startswith(Path(BEETS_IMPORT_PATH).as_posix().rstrip("/")):
        # d’abord simple remplacement de préfixe
        host_guess = _beets_to_host_via_prefix(raw)
        rel = _safe_relative_to(host_guess, Path(MUSIC_IMPORT_PATH))
        if rel is not None:
            return host_guess, rel
        # sinon, tente convert_path_format
        host_conv = _beets_to_host_via_converter(raw)
        rel = _safe_relative_to(host_conv, Path(MUSIC_IMPORT_PATH))
        if rel is not None:
            return host_conv, rel

    # 3) Fallback “ancre /imports/” (cd1; cd2 + chemins bizarres)
    parts = PurePosixPath(raw.as_posix()).parts
    if "imports" in parts:
        idx = parts.index("imports")
        suffix = "/".join(parts[idx + 1:])  # Artist/Album[/CD1]
        rebuilt = Path(MUSIC_IMPORT_PATH) / suffix
        return rebuilt, suffix

    return None
