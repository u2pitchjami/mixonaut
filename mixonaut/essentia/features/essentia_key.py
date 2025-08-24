"""
2025-08-20.

modules de traitement de la key de la track.
"""

from __future__ import annotations

from typing import Any, Optional, TypedDict, TypeGuard, cast

from mixonaut.utils.config import CAMELOT_MAP, ENHARMONIC_MAP


class Candidate(TypedDict):
    key: str | None
    scale: str | None
    strength: float | None


def has_key_and_strength(c: Candidate) -> TypeGuard[Candidate]:
    """Narrow: conserve seulement les candidats avec key et strength présents."""
    return bool(c["key"]) and c["strength"] is not None


def strength_val(c: Candidate) -> float:
    """
    Valeur sûre (non-Optional) pour key= de max().
    """
    # Ici on ne suppose rien : si None -> -inf pour être toujours dominé
    return c["strength"] if c["strength"] is not None else float("-inf")


def convert_to_camelot(key: str, scale: str) -> str | None:
    """
    Convert musical key + scale to Camelot notation.

    Examples:
        F#, major => 2B
        F#m       => 11A
    """
    if not key or not scale:
        return None

    # Clean and normalize key
    key = key.replace("\u266f", "#").replace("\u266d", "b").strip()  # ♯ and ♭
    key = ENHARMONIC_MAP.get(key, key)

    label = f"{key}{'m' if scale.lower() == 'minor' else ''}"
    return CAMELOT_MAP.get(label)


def get_best_key_from_essentia(
    track_features: dict[str, Any], threshold: float = 5.0
) -> Candidate | None:
    """
    Sélectionne la tonalité la plus fiable, avec priorité à edma.

    Si un autre algo a une probabilité significativement plus élevée (> threshold), alors il est préféré à edma.
    """
    candidates: dict[str, Candidate] = {
        "edma": {
            "key": cast(Optional[str], track_features.get("key_edma")),
            "scale": cast(Optional[str], track_features.get("scale_edma")),
            "strength": cast(Optional[float], track_features.get("strength_edma")),
        },
        "krumhansl": {
            "key": cast(Optional[str], track_features.get("key_krumhansl")),
            "scale": cast(Optional[str], track_features.get("scale_krumhansl")),
            "strength": cast(Optional[float], track_features.get("strength_krumhansl")),
        },
        "temperley": {
            "key": cast(Optional[str], track_features.get("key_temperley")),
            "scale": cast(Optional[str], track_features.get("scale_temperley")),
            "strength": cast(Optional[float], track_features.get("strength_temperley")),
        },
    }

    edma = candidates["edma"]

    # Fallback total : si edma n’a pas de key ou pas de strength, on prend le meilleur score dispo
    if not edma["key"] or edma["strength"] is None:
        best = max(
            (data for data in candidates.values() if has_key_and_strength(data)),
            key=strength_val,
            default=None,
        )
        return best

    # Sinon on cherche le meilleur non-edma comparable
    best_non_edma = max(
        (
            data
            for name, data in candidates.items()
            if name != "edma" and has_key_and_strength(data)
        ),
        key=strength_val,
        default=None,
    )

    if (
        best_non_edma
        and best_non_edma["strength"] is not None
        and edma["strength"] is not None
    ):
        if (best_non_edma["strength"] - edma["strength"]) > threshold:
            return best_non_edma

    return edma


# # Optional test
# if __name__ == "__main__":
#     tests = [
#         ("F#", "major"),
#         ("Gb", "major"),
#         ("F♯", "major"),
#         ("A", "minor"),
#         ("Bb", "minor")
#     ]
#     for key, scale in tests:
#         print(f"{key} {scale} => {convert_to_camelot(key, scale)}")
