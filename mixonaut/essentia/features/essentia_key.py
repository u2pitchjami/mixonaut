"""
2025-08-20.

modules de traitement de la key de la track.
"""

from mixonaut.utils.config import CAMELOT_MAP, ENHARMONIC_MAP


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


def get_best_key_from_essentia(track_features: dict, threshold: float = 5.0):
    """
    Sélectionne la tonalité la plus fiable, avec priorité à edma.

    Si un autre algo a une probabilité significativement plus élevée (> threshold), alors il est préféré à edma.
    """
    candidates = {
        "edma": {
            "key": track_features.get("key_edma"),
            "scale": track_features.get("scale_edma"),
            "strength": track_features.get("strength_edma"),
        },
        "krumhansl": {
            "key": track_features.get("key_krumhansl"),
            "scale": track_features.get("scale_krumhansl"),
            "strength": track_features.get("strength_krumhansl"),
        },
        "temperley": {
            "key": track_features.get("key_temperley"),
            "scale": track_features.get("scale_temperley"),
            "strength": track_features.get("strength_temperley"),
        },
    }
    edma = candidates["edma"]
    if not edma["key"] or edma["strength"] is None:
        # fallback total sur le meilleur score
        best = max(
            (
                data
                for data in candidates.values()
                if data["key"] and data["strength"] is not None
            ),
            key=lambda x: x["strength"],
            default=None,
        )
        return best

    best_non_edma = max(
        (
            data
            for k, data in candidates.items()
            if k != "edma" and data["key"] and data["strength"] is not None
        ),
        key=lambda x: x["strength"],
        default=None,
    )
    if best_non_edma and best_non_edma["strength"] - edma["strength"] > threshold:
        return best_non_edma
    else:
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
