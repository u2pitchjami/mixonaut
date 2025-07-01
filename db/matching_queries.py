from db.access import select_one, select_all
from utils.logger import get_logger, with_child_logger

@with_child_logger
def get_track_features(track_id: int, logger: str = None) -> tuple | None:
    query = """
    SELECT bpm, initial_key, beat_intensity, mood_emb_1, mood_emb_2, genre_emb_1, genre_emb_2, duration
    FROM audio_features
    WHERE id = ?
    """
    return select_one(query, (track_id,), logger=logger)

@with_child_logger
def get_transpositions(track_id: int, logger: str = None) -> tuple | None:
    return select_one("SELECT * FROM track_transpositions WHERE id = ?", (track_id,), logger=logger)

@with_child_logger
def get_candidate_tracks(track_id: int, logger: str = None) -> list[tuple]:
    query = """
    SELECT id, bpm, initial_key, beat_intensity, mood_emb_1, mood_emb_2, genre_emb_1, genre_emb_2, duration
    FROM audio_features
    WHERE id != ?
    """
    return select_all(query, (track_id,), logger=logger)

@with_child_logger
def enrich_matches_with_metadata(matches: list[dict], logger: str = None) -> list[dict]:
    for match in matches:
        row = select_one(
            "SELECT artist, album, title FROM items WHERE id = ?",
            (match["track_id"],),
            logger=logger
        )
        if row:
            match["artist"], match["album"], match["title"] = row
        else:
            match["artist"], match["album"], match["title"] = "Unknown", "Unknown", "Unknown"
    return matches