import sqlite3
from pathlib import Path
MIX_DB = "/home/pipo/data/db/mix_assist/mix_assist.db"

with sqlite3.connect(MIX_DB) as conn:
    cursor = conn.cursor()

    # Récupérer tous les enregistrements de tracks
    cursor.execute("SELECT id, * FROM tracks")
    tracks = cursor.fetchall()

    # Colonnes à migrer (doivent exister dans les 2 tables)
    audio_fields = [
        "average_loudness", "chords_changes_rate", "chords_key", "chords_number_rate",
        "chords_scale", "rhythm_danceability", "beats_count", "bpm_essentia",
        "beats_loudness_mean", "danceable", "danceability", "gender", "gender_probability",
        "genre_dortmund", "genre_dortmund_probability", "genre_electronic",
        "genre_electronic_probability", "genre_rosamerica", "genre_rosamerica_probability",
        "genre_tzanetakis", "genre_tzanetakis_probability", "ismir04_rhythm",
        "ismir04_rhythm_probability", "mood_acoustic", "mood_acoustic_probability",
        "mood_aggressive", "mood_aggressive_probability", "mood_electronic",
        "mood_electronic_probability", "mood_happy", "mood_happy_probability",
        "mood_party", "mood_party_probability", "mood_relaxed", "mood_relaxed_probability",
        "mood_sad", "mood_sad_probability", "moods_mirex", "moods_mirex_probability",
        "timbre", "timbre_probability", "tonal_atonal", "tonal_atonal_probability",
        "voice_instrumental", "voice_instrumental_probability", "essentia_json"
    ]

    # Pour chaque track, copier les champs audio dans audio_features
    for track in tracks:
        row = dict(zip([col[0] for col in cursor.description], track))
        values = [row.get(f, None) for f in audio_fields]
        placeholders = ", ".join("?" for _ in audio_fields)
        field_list = ", ".join(audio_fields)

        cursor.execute(f"""
            INSERT INTO audio_features (track_id, {field_list})
            VALUES (?, {placeholders})
        """, [row["id"]] + values)

    conn.commit()
    print("✅ Migration terminée (temporaire)")

