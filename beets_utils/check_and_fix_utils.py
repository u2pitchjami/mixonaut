import os

def is_missing_genre(val):
    if not val or val in {"", "unknown", "none", "?"}:
        return False
    return True

def is_missing_mb_albumid(val):
    if not val or val in {"", "unknown", "none", "?"}:
        return False
    return True
  
def is_missing_gain(val):
    return not val or val.strip() in {"0", "unknown", "none"}


def is_missing_bpm(val):
    try:
        return float(val) < 40
    except (ValueError, TypeError):
        return True

def is_missing_key(val):
    VALID_CAMELOT_KEYS = {f"{i}{k}" for i in range(1, 13) for k in ("A", "B")}
    if not val or val.strip().lower() in {"unknown", "none", "?", "n/a"}:
        return True
    return val.strip().upper() not in VALID_CAMELOT_KEYS