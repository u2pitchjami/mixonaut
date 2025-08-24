from __future__ import annotations

import os
from pathlib import Path
from typing import Union

PathLikeStr = os.PathLike[str]
PathLikeBytes = os.PathLike[bytes]
Pathish = Union[str, bytes, PathLikeStr, PathLikeBytes]


def ensure_to_str(path: Pathish) -> str:
    """
    Retourne un chemin en str (robuste aux bytes via os.fsdecode).
    """
    return os.fsdecode(path)


def ensure_to_path(path: Pathish) -> Path:
    """
    Retourne un pathlib.Path, en décodant proprement si bytes.
    """
    # fsdecode -> str ; Path(str) est sûr et mypy-friendly
    return Path(os.fsdecode(path))


# facultatif si tu as besoin de bytes pour certains APIs
def ensure_to_bytes(path: Pathish) -> bytes:
    """
    Retourne un chemin en bytes (robuste aux str/Path via os.fsencode).
    """
    return os.fsencode(path)
