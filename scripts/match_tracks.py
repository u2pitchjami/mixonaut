from math import isclose
from db.queries import get_track_by_id, get_all_tracks_except  # à adapter à ta base
from essentia.standard import MonoLoader, Energy
from utils.logger import get_logger

logger = get_logger("Match_Tracks")

SEMITONE_MAP = {
    "1A": 1, "2A": 2, "3A": 3, "4A": 4, "5A": 5, "6A": 6,
    "7A": 7, "8A": 8, "9A": 9, "10A": 10, "11A": 11, "12A": 12,
    "1B": 13, "2B": 14, "3B": 15, "4B": 16, "5B": 17, "6B": 18,
    "7B": 19, "8B": 20, "9B": 21, "10B": 22, "11B": 23, "12B": 24,
}

def camelot_to_number(key):
    return SEMITONE_MAP.get(key.upper(), -1)

def are_adjacent_keys(k1, k2):
    return abs(camelot_to_number(k1) - camelot_to_number(k2)) in (1, 11, 12)

def are_relative_major_minor(k1, k2):
    # 8A <-> 5B par exemple
    rel = {
        "1A": "10B", "2A": "11B", "3A": "12B", "4A": "1B", "5A": "2B", "6A": "3B",
        "7A": "4B", "8A": "5B", "9A": "6B", "10A": "7B", "11A": "8B", "12A": "9B"
    }
    return rel.get(k1) == k2 or rel.get(k2) == k1

def compute_energy(path: str) -> float:
    try:
        audio = MonoLoader(filename=path)()
        energy = Energy()(audio)
        return round(energy, 4)
    except Exception as e:
        logging.warning("Erreur calcul énergie sur %s : %s", path, e)
        return 0.0

def compatibility_score(ref, cand):
    key_score = 1.0 if ref["key"] == cand["key"] else (
        0.9 if are_adjacent_keys(ref["key"], cand["key"]) else (
            0.8 if are_relative_major_minor(ref["key"], cand["key"]) else 0.0
        )
    )

    bpm_score = max(0, 1 - abs(ref["bpm"] - cand["bpm"]) / ref["bpm"])
    energy_score = max(0, 1 - abs(ref["energy"] - cand["energy"]) / max(ref["energy"], 0.01))

    return round(0.4 * key_score + 0.3 * bpm_score + 0.3 * energy_score, 2)

def find_compatible_tracks(reference_id: int):
    ref = get_track_by_id(reference_id)
    ref["energy"] = compute_energy(ref["path"])

    candidates = get_all_tracks_except(reference_id)
    results = []
    for track in candidates:
        track["energy"] = compute_energy(track["path"])
        score = compatibility_score(ref, track)
        results.append({
            "id": track["id"],
            "title": track["title"],
            "key": track["key"],
            "bpm": track["bpm"],
            "score": score
        })

    sorted_results = sorted(results, key=lambda x: x["score"], reverse=True)
    return sorted_results

def print_matches(track_id):
    matches = find_compatible_tracks(track_id)
    print(f"🎧 Résultats pour le track ID {track_id}")
    for m in matches[:10]:  # top 10
        print(f"{m['score']*100:.0f}% — {m['title']} (Key: {m['key']}, BPM: {m['bpm']})")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--track-id", type=int, required=True, help="ID du morceau de référence")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    print_matches(args.track_id)








def match_score(track_a: dict, track_b: dict) -> float:
    # 1. Key compatibility
    key_a = track_a.get("key_transposed")
    key_b = track_b.get("key_transposed")
    key_diff = abs(key_a - key_b) if key_a is not None and key_b is not None else None
    key_score = {
        0: 1.0,
        1: 0.8,
        2: 0.6
    }.get(key_diff, 0.0) if key_diff is not None else 0.0

    # 2. BPM proximity
    bpm_a = track_a.get("bpm")
    bpm_b = track_b.get("bpm")
    bpm_diff = abs(bpm_a - bpm_b) if bpm_a and bpm_b else None
    if bpm_diff is None:
        bpm_score = 0.0
    elif bpm_diff <= 2:
        bpm_score = 1.0
    elif bpm_diff <= 5:
        bpm_score = 0.8
    elif bpm_diff <= 10:
        bpm_score = 0.5
    else:
        bpm_score = 0.0

    # 3. Energy level proximity
    e1 = track_a.get("energy_level")
    e2 = track_b.get("energy_level")
    energy_score = 1 - abs(e1 - e2) if e1 is not None and e2 is not None else 0.0

    # 4. Beat intensity proximity
    b1 = track_a.get("beat_intensity")
    b2 = track_b.get("beat_intensity")
    beat_score = 1 - abs(b1 - b2) if b1 is not None and b2 is not None else 0.0

    # Pondération
    score = round(
        0.4 * key_score +
        0.2 * bpm_score +
        0.2 * energy_score +
        0.2 * beat_score,
        3
    )
    return score
