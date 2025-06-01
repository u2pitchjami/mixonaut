CAMELOT_MAP = {
    "C":  "8B", "C#": "3B", "D":  "10B", "D#": "5B", "E":  "12B", "F":  "7B",
    "F#": "2B", "G":  "9B", "G#": "4B", "A":  "11B", "A#": "6B", "B":  "1B",
    "Cm": "5A", "C#m":"12A", "Dm": "7A", "D#m":"2A", "Em": "9A", "Fm": "4A",
    "F#m":"11A", "Gm": "6A", "G#m":"1A", "Am": "8A", "A#m":"3A", "Bm": "10A"
}

# Normalize towards the keys used in CAMELOT_MAP (favor sharps)
ENHARMONIC_MAP = {
    "Db": "C#", "Eb": "D#", "Bb": "A#", "Ab": "G#", "Gb": "F#",
    "C#": "C#", "D#": "D#", "F#": "F#", "G#": "G#", "A#": "A#"
}

def convert_to_camelot(key: str, scale: str) -> str:
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

def get_best_key_from_essentia(track_features: dict):
    """
    Sélectionne la tonalité la plus fiable en fonction de la plus grande strength
    parmi les 3 analyseurs : edma, krumhansl, temperley.
    """
    candidates = {
        "edma": {
            "key": track_features.get("key_edma"),
            "scale": track_features.get("scale_edma"),
            "strength": track_features.get("strength_edma")
        },
        "krumhansl": {
            "key": track_features.get("key_krumhansl"),
            "scale": track_features.get("scale_krumhansl"),
            "strength": track_features.get("strength_krumhansl")
        },
        "temperley": {
            "key": track_features.get("key_temperley"),
            "scale": track_features.get("scale_temperley"),
            "strength": track_features.get("strength_temperley")
        }
    }

    best = None
    max_strength = -1

    for algo, data in candidates.items():
        if data["key"] and data["strength"] is not None:
            if data["strength"] > max_strength:
                max_strength = data["strength"]
                best = {
                    "algorithm": algo,
                    "key": data["key"],
                    "scale": data["scale"],
                    "strength": data["strength"]
                }

    return best  # dict or None

# Optional test
if __name__ == "__main__":
    tests = [
        ("F#", "major"),
        ("Gb", "major"),
        ("F♯", "major"),
        ("A", "minor"),
        ("Bb", "minor")
    ]
    for key, scale in tests:
        print(f"{key} {scale} => {convert_to_camelot(key, scale)}")
