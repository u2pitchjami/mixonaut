# sync_mix_assist_to_beets.py

from beets.library import Library
from beets import config
import sqlite3

MIX_DB = "mix_assist.sqlite"  # à adapter selon ton setup
BEETS_DB = config["library"].as_filename()

def fetch_mix_features():
    """Récupère les features enrichies depuis mix_assist"""
    query = """
    SELECT beet_id, energy_level, beat_intensity
    FROM tracks
    WHERE beet_id IS NOT NULL
    """
    conn = sqlite3.connect(MIX_DB)
    cursor = conn.cursor()
    cursor.execute(query)
    return cursor.fetchall()

def sync_to_beets():
    lib = Library(BEETS_DB)
    updated = 0

    for beet_id, energy_level, beat_intensity in fetch_mix_features():
        if not beet_id:
            continue

        # Recherche dans la lib Beets
        item = lib.items(query=f"mb_trackid:{beet_id}").get()
        if item:
            if energy_level is not None:
                item['energy_level'] = energy_level
            if beat_intensity is not None:
                item['beat_intensity'] = beat_intensity
            item.store()
            updated += 1

    print(f"✅ {updated} morceaux mis à jour dans la bibliothèque Beets")

if __name__ == "__main__":
    sync_to_beets()
