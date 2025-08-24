"""
safe_cast.py - Helpers de conversion robustes et typés
"""

from __future__ import annotations

from typing import Any


def safe_int(val: Any) -> int | None:
    """
    Essaie de convertir val en int.

    Accepte int, float, str numérique. Retourne None si invalide.
    """
    try:
        if isinstance(val, int):
            return val
        if isinstance(val, float):
            return int(val)
        if isinstance(val, str):
            return int(val.strip())
        return None
    except (TypeError, ValueError):
        return None


def safe_float(val: Any) -> float | None:
    """
    Essaie de convertir val en float.

    Accepte int, float, str numérique. Retourne None si invalide.
    """
    try:
        if isinstance(val, (int, float)):
            return float(val)
        if isinstance(val, str):
            return float(val.strip())
        return None
    except (TypeError, ValueError):
        return None


def safe_str(val: Any) -> str | None:
    """
    Force la conversion en str si possible.

    Retourne None si val est None.
    """
    if val is None:
        return None
    try:
        return str(val)
    except Exception:  # pylint: disable=broad-except
        return None
