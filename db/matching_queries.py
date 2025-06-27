from db.access import select_one, select_all
from utils.logger import get_logger
logname = __name__.split(".")[-1]
logger = get_logger(logname)

def get_track_features(track_id: int, logname: str) -> tuple | None:
    query = """
    SELECT bpm, initial_key, mood, beat_intensity, mood_emb_1, mood_emb_2, genre_emb_1, genre_emb_2, duration
    FROM audio_features
    WHERE id = ?
    """
    return select_one(query, (track_id,), logname=logname)

def get_transpositions(track_id: int, logname: str) -> tuple | None:
    return select_one("SELECT * FROM track_transpositions WHERE id = ?", (track_id,), logname=logname)

def get_candidate_tracks(track_id: int, logname: str) -> list[tuple]:
    query = """
    SELECT id, bpm, initial_key, mood, beat_intensity, mood_emb_1, mood_emb_2, genre_emb_1, genre_emb_2, duration
    FROM audio_features
    WHERE id != ?
    """
    return select_all(query, (track_id,), logname=logname)


def enrich_matches_with_metadata(matches: list[dict]) -> list[dict]:
    for match in matches:
        row = select_one(
            "SELECT artist, album, title FROM items WHERE id = ?",
            (match["track_id"],),
            logname=logname
        )
        if row:
            match["artist"], match["album"], match["title"] = row
        else:
            match["artist"], match["album"], match["title"] = "Unknown", "Unknown", "Unknown"
    return matches